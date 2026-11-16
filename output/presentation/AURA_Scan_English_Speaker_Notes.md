# AURA Scan: English presentation script

## Slide 1

AURA Scan is a web prototype that reads health instrument screens through a live camera. It automatically records stable observations, preserves their evidence and brings them into a health history. Our demonstration uses fictional data. We aim to support a crew member and the mission medical team. We do not claim clinical diagnostic capability or NASA approval.

## Slide 2

NASA groups human spaceflight challenges into five hazards. Its Human Research Program studies their effects on health and performance. Our focus is a practical software gap: a number shown on a device can be lost, copied incorrectly or separated from its context. AURA Scan helps collect that evidence in one place. A reading alone cannot identify the cause of a symptom.

## Slide 3

The user enters an astronaut alias and starts the camera. The browser periodically sends a frame to our Python service. OCR associates numbers with visible labels and units. The stability check requires at least three consistent frames over at least three seconds. AURA Scan saves one observation and avoids repeatedly saving an unchanged screen. The saved observation stays unreviewed until a person checks its evidence.

## Slide 4

We improved the capture path to preserve more detail, added an adjustable reading area and request continuous focus and exposure when a camera exposes those controls. If the first OCR pass is incomplete, local contrast enhancement provides a second attempt. The application does not merge conflicting numbers. These changes cannot reconstruct digits that a strong reflection completely hides. The interface therefore gives practical repositioning guidance. Physical device testing remains necessary.

## Slide 5

The demonstration does not depend on the lighting at the event. We click Simulación, and the same OCR processes three synthetic screens. The scenario contains a baseline blood pressure, a follow-up and an oximeter reading. The application labels all values and times as fictional and stores scripted provenance. The guide then takes us through history, the assistant and the report. This demonstrates the software workflow, not accuracy on real instruments.

## Slide 6

The history preserves both pressure readings for the same fictional astronaut. Systolic pressure changes from 120 to 126 millimeters of mercury, a difference of six. Diastolic pressure changes from 80 to 82, a difference of two. These are numerical differences. Their clinical meaning would require the real timing, technique, instrument and patient context. The application keeps those distinctions visible instead of turning every change into a diagnosis.

## Slide 7

The assistant combines the available record with declared sleep, mood, symptoms and mission environment. It gives follow-up suggestions with a reason and a source link. For example, it can ask the crew to improve measurement context or discuss persistent poor wellbeing with mission support. This version uses explicit rules. It does not send health data to an external generative AI service, and it does not prescribe treatment or produce a medical diagnosis.

## Slide 8

We use every resource supplied for the challenge. NASA hazards explain mission context. The risks overview identifies relevant domains without becoming a treatment catalog. Ongoing HRP research supports consistent follow-up over time. The CSA radiation article shows why exposure needs a dedicated detector. The CSA science resource supports preparation for longer and more autonomous missions. We also use FDA and MedlinePlus references for instrument limitations and declared warning signs.

## Slide 9

The browser handles the live view and the user interface. A FastAPI service runs OpenCV and RapidOCR, checks consistency and applies the follow-up rules. A persistent Railway volume stores the database, accepted evidence and audit records. Browser cookies isolate workspaces without requiring an account. That also means losing a cookie can lose access to that workspace. A real mission deployment would need stronger identity, continuity, retention and recovery procedures.

## Slide 10

Our evidence supports the software workflow: live frame processing, automatic observations, deduplication, review, history and the guided demonstration. It does not establish clinical accuracy. We still need a labeled dataset and physical tests across devices, glare, angles and motion, followed by clinical and operational review. For the presentation, the guided simulation provides a repeatable walkthrough while clearly labeling every value as fictional. Thank you.

## Live demonstration checklist

1. Open the deployed web app and click Simulación.
2. Explain that the three screens and their measurement times are fictional.
3. Click Siguiente: Historial and show the two blood pressure records.
4. Click Siguiente: Asistente and select ¿Qué ha cambiado? to show +6 and +2 mmHg.
5. Point out the source links and missing-data limitations.
6. Continue to Informe and download the sample PDF.
7. Return to the camera. If demonstrating a real instrument, fill the frame with its complete display, including labels and units. Adjust the angle to remove glare.
