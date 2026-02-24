# Fake data in memory
fake_aadhaar = {
    "123456789012": {"name": "Ramesh Kumar", "eligible": True},
    "111122223333": {"name": "Sita Devi", "eligible": True},
    "999988887777": {"name": "Amit Sharma", "eligible": False}
}

fake_ration = {
    "RC1001": {"family": ["Ramesh Kumar", "Sita Devi"], "eligible": True},
    "RC2002": {"family": ["Amit Sharma"], "eligible": False}
}

fake_hospitals = [
    {"state": "Bihar", "pincode": "800001", "hospital": "AIIMS Patna"},
    {"state": "Bihar", "pincode": "800001", "hospital": "IGIMS Patna"},
    {"state": "Delhi", "pincode": "110001", "hospital": "AIIMS Delhi"},
    {"state": "Up", "pincode": "201301", "hospital": "Max Hospital Noida"},
]


def check_multiple_aadhaar(numbers):
    """Check multiple Aadhaar numbers"""
    results = []
    for num in numbers:
        num = num.strip()
        if num in fake_aadhaar:
            record = fake_aadhaar[num]
            status = "✅ Eligible" if record["eligible"] else "❌ Not Eligible"
            results.append(f"{record['name']} - {status}")
        else:
            results.append(f"{num} - Not Found ⚠️")
    return results


def check_ration(ration):
    """Check ration card"""
    ration = ration.strip()
    if ration in fake_ration:
        return fake_ration[ration]
    return None


def search_hospital(state, pincode):
    """Search hospitals by state and pincode"""
    results = []
    for h in fake_hospitals:
        if h["state"].lower() == state.lower() and h["pincode"] == pincode:
            results.append(h)
    return results