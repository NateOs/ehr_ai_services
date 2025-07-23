core features to focus on:

API Endpoints:
all endpoints will require auth, not necessarily user auth, more like if the user is from tenant A, and has login token allow...
some of these are going to be background processes that will populate the db without active user interaction.

//  for the professional
[] POST /api/v1/analyze/results
   - takes in either a file and text data or just text data
   - Flag abnormal results or provide diagnostic insights

[] GET /api/v1/patient/{id}/summary
   - should get last records of patient and perform analysis then return reponse
   - Generate patient history summary

[] POST /api/v1/suggest/codes
   - based on training data
   - Suggest ICD-10 and CPT codes based on clinical notes

// for the patient
[] POST /api/v1/explain/medical
   - Provide patient-friendly explanations of medical terms or conditions

[] POST /api/v1/explain/medication
   - Generate layperson-friendly medication explanations

[] POST /api/v1/interpret/lab-results
   - Interpret and explain lab results in simple terms

// for the professional
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
   - will accept files, images, text data?

Multitenancy
- separate instances in terms of vdb, training_data...
- there should be a general table too for general medical inferences

- if user has already been authenticated in ehr, how do we persist the same auth credential?
- also what to do when the user logs out?