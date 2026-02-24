from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017/")
db = client["pmjay_demo"]

db.aadhaar.delete_many({})
db.ration.delete_many({})
db.hospitals.delete_many({})

db.aadhaar.insert_many([
    {"aadhaar": "123456789012", "name": "Ramesh Kumar", "eligible": True},
    {"aadhaar": "111122223333", "name": "Sita Devi", "eligible": True},
    {"aadhaar": "999988887777", "name": "Amit Sharma", "eligible": False}
])

db.ration.insert_many([
    {"ration_card": "RC1001", "family": ["Ramesh Kumar", "Sita Devi"], "eligible": True},
    {"ration_card": "RC2002", "family": ["Amit Sharma"], "eligible": False}
])

db.hospitals.insert_many([
    {"state": "Bihar", "pincode": "800001", "hospital": "AIIMS Patna"},
    {"state": "Bihar", "pincode": "800001", "hospital": "IGIMS Patna"},
    {"state": "Delhi", "pincode": "110001", "hospital": "AIIMS Delhi"}
])

print("Database seeded successfully")
