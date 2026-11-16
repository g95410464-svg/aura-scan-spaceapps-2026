from io import BytesIO
from pypdf import PdfReader
from tests.conftest import confirmation


def pdf_text(response):
    assert response.status_code == 200
    return '\n'.join(page.extract_text() for page in PdfReader(BytesIO(response.content)).pages)


def test_report_defaults_to_english_and_can_switch_without_mutating_data(visitor_client, capture):
    # These user strings also appear in the translation catalog. They must remain literal.
    body = confirmation(subject_alias='Pulso', symptoms='Presión sistólica')
    result = visitor_client.post(f'/api/captures/{capture["id"]}/confirm', json=body).json()
    path = f'/api/measurements/{result["id"]}/report.pdf'
    english = visitor_client.get(path)
    text = pdf_text(english)
    assert english.headers['content-language'] == 'en'
    assert 'Measurement report' in text and 'Systolic pressure' in text and 'bpm' in text
    assert 'Astronaut (alias): Pulso' in text and 'Presión sistólica' in text
    spanish = visitor_client.get(path, params={'lang': 'es'})
    text = pdf_text(spanish)
    assert spanish.headers['content-language'] == 'es'
    assert 'Informe de mediciones' in text and 'Presión sistólica' in text and 'lpm' in text
    saved = visitor_client.get('/api/measurements').json()['items'][0]
    assert saved['subject_alias'] == 'Pulso' and saved['symptoms'] == 'Presión sistólica'
    assert saved['readings'] == result['readings']
    assert visitor_client.get(path, params={'lang': 'fr'}).status_code == 422
