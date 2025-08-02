
Multitenancy
- separate instances in terms of vdb, training_data...
- there should be a general table too for general medical inferences

- if user has already been authenticated in ehr, how do we persist the same auth credential?
- also what to do when the user logs out?, log out from ai as well


Auth and DB setup
- Use user first login to determine facility and create vector db
- add end point to delete data, only available to admin user

VectorDB_Facility_A
  |- User_1_Collection
  |- User_2_Collection
  |- Facility_Shared_Collection

VectorDB_Facility_B
  |- User_3_Collection
  |- User_4_Collection
  |- Facility_Shared_Collection

VectorDB_General_Medical_Knowledge

Considering your specific use case in healthcare, here's a suggested approach:
1.
Hybrid Model: 
Create a vector database per facility or tenant, rather than per individual user.
Maintain a general vector database for common medical knowledge.
2.
User-Specific Collections:
Within each facility's vector database, use collections or namespaces to separate data by user.
3.
Shared Knowledge:
Use the general medical knowledge database to supplement user-specific queries, especially for new users with limited data.
4.
Tiered Structure:
Implement a tiered structure: General Medical Knowledge -> Facility-Specific Knowledge -> User-Specific Data.
Implementation Considerations:
1.
Use a vector database that supports multi-tenancy natively, like Pinecone or Weaviate.
2.
Implement robust access control to ensure users can only access their own data within the shared database.
3.
Use efficient indexing strategies to maintain performance as the data grows.
4.
Implement a background process to periodically update the general medical knowledge database.
5.
Consider a caching layer for frequently accessed data to improve performance.

the facility should also be identifiable by its external id