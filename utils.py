class ClassMeet():
    def __init__(self):
        self.type = 0
        self.type_str= "OM - Poczatkujacy"
        self.date = "2024-12-31"
        self.time = "20:00-21:30"
        self.host = "Filip Manijak"
        self.description = "Super koło"
    def load_from_discord(self, type_value, date, time, host, description):
        self.type = int(type_value)
        self.date = date
        self.time = time
        self.host = host
        self.description = description
        mapping = {
            0: "OM - Poczatkujacy",
            1: "OM - Srednia",
            2: "OM - Final++",
            3: "OAI",
            4: "OF",
            5: "OI",
        }
        self.type_str = mapping.get(self.type, self.type_str)
def user_class_match(class_type, user_roles):
    """
    Returns True if any role in user_roles matches the class_type.
    Comparison is case-insensitive and accepts some common variants.
    """
    # map class_type -> acceptable role name fragments (lowercase)
    role_map = {
        0: ["poczatkujacy"],
        1: ["srednia"],
        2: ["final", "final++"],
        3: ["ai"],
        4: ["fizyka"],
        5: ["informatyka", "infa"],
    }
    candidates = role_map.get(int(class_type), [])
    for role in user_roles:
        rn = getattr(role, "name", "").lower()
        for c in candidates:
            if c in rn:
                return True
    return False



