core features to focus on:

API Endpoints:
[] POST /api/v1/analyze/results
   - Flag abnormal results or provide diagnostic insights

[] GET /api/v1/patient/{id}/summary
   - Generate patient history summary

[] POST /api/v1/suggest/codes
   - Suggest ICD-10 and CPT codes based on clinical notes

[] POST /api/v1/explain/medical
   - Provide patient-friendly explanations of medical terms or conditions

[] POST /api/v1/explain/medication
   - Generate layperson-friendly medication explanations

[] POST /api/v1/interpret/lab-results
   - Interpret and explain lab results in simple terms

[] POST /api/v1/query/clinical
   - Allow natural language queries on patient data

[] POST /api/v1/generate/clinical-notes
   - Assist in generating clinical notes

[] POST /api/v1/generate/discharge-instructions
   - Create patient education and discharge instructions

[] GET /api/v1/security/audit-log
   - Retrieve HIPAA-compliant audit logs of AI interactions

[] POST /api/v1/chat/patient-portal
   - Handle patient queries through a chatbot interface

[] POST /training_endpoint

Multitenancy
- separate instances in terms of vdb, training_data...
- there should be a general table too for general medical inferences