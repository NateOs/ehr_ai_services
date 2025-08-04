# Functional Testing Case Stories – AI Integration in EHR System

This document outlines functional case stories based on the AI modules defined in the AI Integration Documentation for EHR systems. Each story includes relevant test case ideas to ensure comprehensive coverage.

---

## 🩺 1. Diagnostic Support

**Case Story:**  
Dr. Mensah opens a patient chart. The system automatically summarizes the patient’s medical history (from past notes, labs, vitals). As Dr. Mensah enters new findings, the AI suggests possible differential diagnoses and highlights a critically low hemoglobin level. It flags a potential diagnostic oversight, suggesting *Chronic Myeloid Leukemia* with an explanation in clinical reasoning terms.

**Test Cases:**
- Verify auto-summarization triggers on chart load.
- Validate AI-generated alerts for abnormal or urgent lab values.
- Ensure differential diagnoses include accessible explanations.
- Check audit logs for AI-generated outputs.

---

## 🧾 2. Coding Assistant

**Case Story:**  
After completing documentation for a patient with respiratory symptoms, Dr. Adjei saves the note. The AI assistant suggests ICD-10 code `J20.9` and CPT code `99213`, with a rationale referencing *acute bronchitis*. Dr. Adjei reviews and adjusts the code before submitting for billing.

**Test Cases:**
- Confirm suggestions trigger on note-save or assessment-entry.
- Validate that each ICD/CPT code is backed by clinical rationale.
- Ensure integration with billing module allows editing pre-submission.
- Check that clinician must approve AI-suggested codes before finalization.

---

## 👨‍⚕️ 3. Medical Explanation

**Case Story:**  
Ama, a patient, views her chart on the patient portal. Next to her anemia diagnosis, an expandable summary explains that low hemoglobin and MCV values indicate likely iron-deficiency anemia in plain language.

**Test Cases:**
- Ensure medical explanations are written in non-technical language.
- Verify output adapts based on up-to-date patient data.
- Test optional UI expansion for summaries.
- Confirm removal or masking of sensitive identifiers.

---

## 💊 4. Medication Explanation

**Case Story:**  
Ama sees a newly prescribed medication: **Simvastatin 40mg**. A tooltip displays:  
"Simvastatin helps lower your cholesterol. It’s taken once daily and works best with a healthy diet..."

**Test Cases:**
- Confirm AI generates layperson-friendly descriptions for any medication.
- Validate mention of key side effects and usage instructions.
- Ensure explanations are dynamically tied to prescription context.

---

## 🧪 5. Lab Results Explanation

**Case Story:**  
Ama reviews her latest lab report and sees the summary:  
"Your Hemoglobin A1c level is 8.1%, which is higher than normal. This suggests your diabetes may not be well controlled."

**Test Cases:**
- Validate correct interpretation based on input values and reference ranges.
- Ensure condition summaries reflect accurate severity and clinical significance.
- Test user interface for displaying explanations alongside results.

---

## 📝 6. Patient Education & Discharge Instructions

**Case Story:**  
After a clinic visit, Kofi receives a personalized follow-up summary including:  
- Reason for visit (e.g., hypertension)  
- Monitoring instructions  
- Next appointment reminders  
- Link to AI-powered FAQ chatbot

**Test Cases:**
- Ensure summaries trigger on encounter close.
- Validate inclusion of visit highlights, diagnosis, next steps.
- Confirm formatting is appropriate for patient readability.
- Check chatbot integration for optional follow-up.

---

## 🧠 7. Clinical Copilot

**Case Story:**  
Dr. Asante asks the system:  
> “What changed since the last visit?”  
The AI responds:  
> “Patient’s blood pressure has risen by 15 mmHg and new complaint of dizziness was recorded.”  
As he types a SOAP note, the system suggests auto-complete text using prior visit context.

**Test Cases:**
- Validate NLP query interpretation and contextual response accuracy.
- Test real-time note suggestions during clinician typing.
- Confirm responses include source references.
- Check input/output behavior under tokenized, secure settings.

---

## 🔒 8. Security and Compliance

**Case Story:**  
While using the EHR, all AI requests are transmitted via HTTPS. No raw PHI is logged. A user without appropriate permissions tries to request an AI explanation and is denied access.

**Test Cases:**
- Validate all API calls use TLS/HTTPS.
- Confirm PHI is anonymized or tokenized before AI interaction.
- Ensure unauthorized users cannot access AI tools.
- Review logs to confirm only de-identified data is stored.

---

## ✅ Summary

These case stories should guide the functional validation of AI modules in the EHR system, covering:

- Patient safety and AI transparency
- Real-time assistance for clinicians
- Education and communication support for patients
- Compliance with HIPAA and ethical AI principles


## Enhanced Initial Testing Sequence:

### 1. Facility Foundation
- [] Create facility (must exist first)
- [] Auto-create facility's VectorDB
- [] Auto-create facility's shared collection
- 🆕 **Validate facility isolation** (queries don't cross facilities)

### 2. Patient Creation & Setup
- [] Create patient (linked to facility)
- [] Auto-create patient's dedicated collection
- 🆕 **Validate patient-facility relationship constraints**
- 🆕 **Test patient anonymization** (patient_code generation)

### 3. Document Upload & Vectorization
- [] Upload facility-level documents → facility vectorization
- [] Upload patient-specific documents → patient vectorization
- 🆕 **Test document type classification** (clinical vs administrative)
- 🆕 **Validate metadata preservation** during vectorization
- 🆕 **Test batch upload scenarios**

### 4. Query Scoping & Intelligence
- [] Facility queries → facility-scoped results + GPT fallback
- [] Patient queries → patient-scoped results only
- 🆕 **Test query escalation** (patient → facility → GPT)
- 🆕 **Validate cross-patient data isolation**
- 🆕 **Test query context preservation** across sessions

### 5. Learning & Optimization
- [] Vectorize query responses for future use
- 🆕 **Test query result caching**
- 🆕 **Validate response quality improvement over time**
- 🆕 **Test vector space optimization**