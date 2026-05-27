# # # backend/phc_recommender.py
# # # Core recommendation logic for NiDaan PHCs

# # import os
# # import sqlite3
# # from math import radians, sin, cos, sqrt, atan2
# # from typing import List, Optional

# # # Define database path
# # BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# # DB_PATH = os.path.join(BASE_DIR, "..", "data", "phc_directory.db")

# # SERVICE_MAP = {
# #     "high": ["OPD", "Delivery Services", "Basic Lab"],
# #     "medium": ["OPD", "Maternal & Child Health"],
# #     "low": ["OPD"],
# #     # Keyword-based additions (check criticality reason string):
# #     "malaria":      ["Malaria Testing"],
# #     "tb":           ["TB DOTS"],
# #     "snake":        ["Snake Bite Treatment"],
# #     "delivery":     ["Delivery Services", "Maternal & Child Health"],
# #     "pregnancy":    ["Maternal & Child Health", "Delivery Services"],
# #     "nutrition":    ["Nutrition Services"],
# #     "immunization": ["Immunization"],
# #     "hiv":          ["HIV Testing"],
# # }

# # def haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
# #     """Calculate the great-circle distance between two points in kilometers."""
# #     R = 6371.0  # Earth radius in km
# #     dlat = radians(lat2 - lat1)
# #     dlng = radians(lng2 - lng1)
# #     a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng / 2) ** 2
# #     c = 2 * atan2(sqrt(a), sqrt(1 - a))
# #     return R * c

# # def recommend_phcs(
# #     district: str,
# #     criticality: str,
# #     required_services: List[str],
# #     patient_lat: Optional[float] = None,
# #     patient_lng: Optional[float] = None
# # ) -> List[dict]:
# #     """
# #     Query the SQLite database for PHCs in the given district.
# #     Ranks them by service match score first, then distance.
# #     Returns the top 3 recommended PHCs.
# #     """
# #     # Normalize inputs
# #     district = district.strip()
# #     criticality = criticality.strip().lower()
    
# #     # Fallback to default services if required_services is empty
# #     if not required_services:
# #         required_services = SERVICE_MAP.get(criticality, ["OPD"])

# #     # Unique list of required services
# #     required_services = list(set(required_services))

# #     if not os.path.exists(DB_PATH):
# #         print(f"Error: Database not found at {DB_PATH}")
# #         return []

# #     try:
# #         conn = sqlite3.connect(DB_PATH)
# #         conn.row_factory = sqlite3.Row
# #         cursor = conn.cursor()

# #         # Query all PHCs in the district
# #         cursor.execute(
# #             "SELECT * FROM phcs WHERE LOWER(district) = LOWER(?)",
# #             (district,)
# #         )
# #         phc_rows = cursor.fetchall()
        
# #         if not phc_rows:
# #             conn.close()
# #             return []

# #         recommendations = []
        
# #         for row in phc_rows:
# #             phc_id = row["id"]
            
# #             # Fetch services for this PHC from phc_services table
# #             cursor.execute(
# #                 "SELECT service FROM phc_services WHERE phc_id = ?",
# #                 (phc_id,)
# #             )
# #             service_rows = cursor.fetchall()
# #             phc_services = [r["service"] for r in service_rows]

# #             # Calculate match score
# #             matched_services = [s for s in required_services if s in phc_services]
            
# #             if not required_services:
# #                 base_score = 1.0
# #             else:
# #                 base_score = len(matched_services) / len(required_services)

# #             # Apply bonuses for high criticality
# #             bonus = 0.0
# #             if criticality == "high":
# #                 if row["open_24hr"] == 1:
# #                     bonus += 0.2
# #                 if row["ambulance"] == 1:
# #                     bonus += 0.1

# #             service_match_score = min(1.0, base_score + bonus)

# #             # Calculate distance
# #             distance_km = None
# #             if (
# #                 patient_lat is not None 
# #                 and patient_lng is not None 
# #                 and row["latitude"] is not None 
# #                 and row["longitude"] is not None
# #             ):
# #                 distance_km = haversine(patient_lat, patient_lng, row["latitude"], row["longitude"])

# #             # Map fields to match PHCResult schema
# #             recommendations.append({
# #                 "id": row["id"],
# #                 "name": row["name"],
# #                 "block": row["block"],
# #                 "address": row["address"],
# #                 "contact": row["contact"],
# #                 "open_24hr": bool(row["open_24hr"]),
# #                 "timing": row["doctor_timing"] or "9AM–4PM Mon–Sat",
# #                 "services": phc_services,
# #                 "ambulance": bool(row["ambulance"]),
# #                 "latitude": row["latitude"],
# #                 "longitude": row["longitude"],
# #                 "distance_km": distance_km,
# #                 "service_match_score": service_match_score,
# #                 "matched_count": len(matched_services),
# #                 "required_count": len(required_services),
# #             })

# #         conn.close()

# #         # Identify nearest if distance is available
# #         has_distance = any(r["distance_km"] is not None for r in recommendations)
# #         nearest_id = None
# #         if has_distance:
# #             valid_distances = [r for r in recommendations if r["distance_km"] is not None]
# #             if valid_distances:
# #                 nearest_item = min(valid_distances, key=lambda x: x["distance_km"])
# #                 nearest_id = nearest_item["id"]

# #         # Generate match reasons
# #         for r in recommendations:
# #             is_nearest = r["id"] == nearest_id
            
# #             # Construct standard, clear reason
# #             if r["required_count"] == 0:
# #                 services_text = "Basic services available."
# #             elif r["matched_count"] == r["required_count"]:
# #                 services_text = f"Matches {r['matched_count']}/{r['required_count']} required services."
# #             elif r["matched_count"] > 0:
# #                 services_text = f"Partial match ({r['matched_count']}/{r['required_count']} services)."
# #             else:
# #                 services_text = f"Matches 0/{r['required_count']} required services."

# #             parts = [services_text]
# #             if r["distance_km"] is not None:
# #                 parts.append(f"{r['distance_km']:.1f} km away.")
# #             elif is_nearest:
# #                 parts.append("Nearest PHC in district.")
# #             else:
# #                 parts.append("Consider if closer PHCs unavailable.")

# #             extra = []
# #             if r["open_24hr"]:
# #                 extra.append("Open 24 hours")
# #             if r["ambulance"]:
# #                 extra.append("Ambulance available")

# #             if extra:
# #                 parts.append(". ".join(extra) + ".")

# #             r["match_reason"] = " ".join(parts)
            
# #             # Clean up temporary counting fields not needed in response schema
# #             del r["matched_count"]
# #             del r["required_count"]

# #         # Rank: service_match_score DESC, distance_km ASC (None last)
# #         recommendations.sort(
# #             key=lambda x: (
# #                 -x["service_match_score"],
# #                 x["distance_km"] if x["distance_km"] is not None else float("inf")
# #             )
# #         )

# #         # Return top 5
# #         return recommendations[:5]

# #     except Exception as e:
# #         print(f"Error in recommend_phcs: {e}")
# #         return []


# # backend/phc_recommender.py
# # Core recommendation logic for NiDaan PHCs

# import os
# import sqlite3
# from math import radians, sin, cos, sqrt, atan2
# from typing import List, Optional

# # Define database path
# BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# DB_PATH = os.path.join(BASE_DIR, "..", "data", "phc_directory.db")

# SERVICE_MAP = {
#     "high": ["OPD", "Delivery Services", "Basic Lab"],
#     "medium": ["OPD", "Maternal & Child Health"],
#     "low": ["OPD"],
#     "malaria":      ["Malaria Testing"],
#     "tb":           ["TB DOTS"],
#     "snake":        ["Snake Bite Treatment"],
#     "delivery":     ["Delivery Services", "Maternal & Child Health"],
#     "pregnancy":    ["Maternal & Child Health", "Delivery Services"],
#     "nutrition":    ["Nutrition Services"],
#     "immunization": ["Immunization"],
#     "hiv":          ["HIV Testing"],
# }

# # Max distance beyond which distance_score becomes 0
# MAX_DISTANCE_KM = 50

# # Scoring weights — must add up to 1.0
# WEIGHT_SERVICE = 0.6
# WEIGHT_DISTANCE = 0.4


# def haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
#     """Calculate the great-circle distance between two points in kilometers."""
#     R = 6371.0
#     dlat = radians(lat2 - lat1)
#     dlng = radians(lng2 - lng1)
#     a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng / 2) ** 2
#     c = 2 * atan2(sqrt(a), sqrt(1 - a))
#     return R * c


# def recommend_phcs(
#     district: str,
#     criticality: str,
#     required_services: List[str],
#     patient_lat: Optional[float] = None,
#     patient_lng: Optional[float] = None
# ) -> List[dict]:
#     """
#     Query the SQLite database for PHCs in the given district.
#     Ranks them by a combined score of service match (60%) and proximity (40%).
#     Returns the top 5 recommended PHCs.
#     """
#     district = district.strip()
#     criticality = criticality.strip().lower()

#     # Debug log — helps verify coordinates are arriving correctly
#     print(f"[recommend_phcs] district={district!r} criticality={criticality!r} "
#           f"lat={patient_lat} lng={patient_lng}")

#     if not required_services:
#         required_services = SERVICE_MAP.get(criticality, ["OPD"])

#     required_services = list(set(required_services))

#     has_patient_location = (
#         patient_lat is not None and patient_lng is not None
#     )

#     if not os.path.exists(DB_PATH):
#         print(f"[recommend_phcs] Error: Database not found at {DB_PATH}")
#         return []

#     try:
#         conn = sqlite3.connect(DB_PATH)
#         conn.row_factory = sqlite3.Row
#         cursor = conn.cursor()

#         cursor.execute(
#             "SELECT * FROM phcs WHERE LOWER(district) = LOWER(?)",
#             (district,)
#         )
#         phc_rows = cursor.fetchall()

#         if not phc_rows:
#             conn.close()
#             return []

#         recommendations = []

#         for row in phc_rows:
#             phc_id = row["id"]

#             cursor.execute(
#                 "SELECT service FROM phc_services WHERE phc_id = ?",
#                 (phc_id,)
#             )
#             service_rows = cursor.fetchall()
#             phc_services = [r["service"] for r in service_rows]

#             # --- Service match score ---
#             matched_services = [s for s in required_services if s in phc_services]
#             if not required_services:
#                 base_score = 1.0
#             else:
#                 base_score = len(matched_services) / len(required_services)

#             # Bonuses for high criticality
#             bonus = 0.0
#             if criticality == "high":
#                 if row["open_24hr"] == 1:
#                     bonus += 0.2
#                 if row["ambulance"] == 1:
#                     bonus += 0.1

#             service_match_score = min(1.0, base_score + bonus)

#             # --- Distance score ---
#             distance_km = None
#             phc_has_coords = (
#                 row["latitude"] is not None and row["longitude"] is not None
#             )

#             if has_patient_location and phc_has_coords:
#                 distance_km = haversine(
#                     patient_lat, patient_lng,
#                     row["latitude"], row["longitude"]
#                 )
#                 distance_score = max(0.0, 1.0 - (distance_km / MAX_DISTANCE_KM))
#             else:
#                 # No coordinates available — penalise but don't eliminate
#                 distance_score = 0.0

#             # --- Combined score ---
#             if has_patient_location:
#                 combined_score = (
#                     service_match_score * WEIGHT_SERVICE +
#                     distance_score * WEIGHT_DISTANCE
#                 )
#             else:
#                 # No patient location — fall back to service score only
#                 combined_score = service_match_score

#             recommendations.append({
#                 "id": row["id"],
#                 "name": row["name"],
#                 "block": row["block"],
#                 "address": row["address"],
#                 "contact": row["contact"],
#                 "open_24hr": bool(row["open_24hr"]),
#                 "timing": row["doctor_timing"] or "9AM–4PM Mon–Sat",
#                 "services": phc_services,
#                 "ambulance": bool(row["ambulance"]),
#                 "latitude": row["latitude"],
#                 "longitude": row["longitude"],
#                 "distance_km": distance_km,
#                 "service_match_score": service_match_score,
#                 "combined_score": combined_score,
#                 "matched_count": len(matched_services),
#                 "required_count": len(required_services),
#             })

#         conn.close()

#         # --- Generate match reasons ---
#         for r in recommendations:
#             parts = []

#             # Service match text
#             if r["required_count"] == 0:
#                 parts.append("Basic services available.")
#             elif r["matched_count"] == r["required_count"]:
#                 parts.append(f"Matches {r['matched_count']}/{r['required_count']} required services.")
#             elif r["matched_count"] > 0:
#                 parts.append(f"Partial match ({r['matched_count']}/{r['required_count']} services).")
#             else:
#                 parts.append(f"Matches 0/{r['required_count']} required services.")

#             # Distance text
#             if r["distance_km"] is not None:
#                 parts.append(f"{r['distance_km']:.1f} km away.")
#             else:
#                 parts.append("Distance unavailable.")

#             # Extras
#             extra = []
#             if r["open_24hr"]:
#                 extra.append("Open 24 hours")
#             if r["ambulance"]:
#                 extra.append("Ambulance available")
#             if extra:
#                 parts.append(". ".join(extra) + ".")

#             r["match_reason"] = " ".join(parts)

#             # Clean up internal fields
#             del r["matched_count"]
#             del r["required_count"]
#             del r["combined_score"]  # not needed in response schema

#         # --- Sort by combined score DESC ---
#         recommendations.sort(key=lambda x: -(
#             (x["service_match_score"] * WEIGHT_SERVICE) +
#             (
#                 max(0.0, 1.0 - (x["distance_km"] / MAX_DISTANCE_KM)) * WEIGHT_DISTANCE
#                 if x["distance_km"] is not None and has_patient_location
#                 else 0.0
#             )
#         ))

#         return recommendations[:5]

#     except Exception as e:
#         print(f"[recommend_phcs] Error: {e}")
#         return []


# backend/phc_recommender.py
# Core recommendation logic for NiDaan PHCs

import os
import sqlite3
from math import radians, sin, cos, sqrt, atan2
from typing import List, Optional

# Define database path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "..", "data", "phc_directory.db")

SERVICE_MAP = {
    "high": ["OPD", "Delivery Services", "Basic Lab"],
    "medium": ["OPD", "Maternal & Child Health"],
    "low": ["OPD"],
    "malaria":      ["Malaria Testing"],
    "tb":           ["TB DOTS"],
    "snake":        ["Snake Bite Treatment"],
    "delivery":     ["Delivery Services", "Maternal & Child Health"],
    "pregnancy":    ["Maternal & Child Health", "Delivery Services"],
    "nutrition":    ["Nutrition Services"],
    "immunization": ["Immunization"],
    "hiv":          ["HIV Testing"],
}

# Max distance beyond which distance_score becomes 0
MAX_DISTANCE_KM = 50

# Scoring weights — must add up to 1.0
WEIGHT_SERVICE = 0.6
WEIGHT_DISTANCE = 0.4


def haversine(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculate the great-circle distance between two points in kilometers."""
    R = 6371.0
    dlat = radians(lat2 - lat1)
    dlng = radians(lng2 - lng1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c


def recommend_phcs(
    district: str,
    criticality: str,
    required_services: List[str],
    patient_lat: Optional[float] = None,
    patient_lng: Optional[float] = None
) -> List[dict]:
    """
    Query the SQLite database for PHCs in the given district.
    Ranks them by a combined score of service match (60%) and proximity (40%).
    Returns the top 5 recommended PHCs.
    """
    district = district.strip()
    criticality = criticality.strip().lower()

    print(f"[recommend_phcs] district={district!r} criticality={criticality!r} "
          f"lat={patient_lat} lng={patient_lng}")

    if not required_services:
        required_services = SERVICE_MAP.get(criticality, ["OPD"])

    required_services = list(set(required_services))

    has_patient_location = (
        patient_lat is not None and patient_lng is not None
    )

    if not os.path.exists(DB_PATH):
        print(f"[recommend_phcs] Error: Database not found at {DB_PATH}")
        return []

    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            "SELECT * FROM phcs WHERE LOWER(district) = LOWER(?)",
            (district,)
        )
        phc_rows = cursor.fetchall()

        if not phc_rows:
            conn.close()
            return []

        recommendations = []

        for row in phc_rows:
            phc_id = row["id"]

            cursor.execute(
                "SELECT service FROM phc_services WHERE phc_id = ?",
                (phc_id,)
            )
            service_rows = cursor.fetchall()
            phc_services = [r["service"] for r in service_rows]

            # --- Service match score ---
            matched_services = [s for s in required_services if s in phc_services]
            if not required_services:
                base_score = 1.0
            else:
                base_score = len(matched_services) / len(required_services)

            # --- Bonuses ---
            bonus = 0.0

            if criticality == "high":
                if row["emergency_capable"] == 1:
                    bonus += 0.25
                if row["open_24hr"] == 1:
                    bonus += 0.15
                if row["ambulance"] == 1:
                    bonus += 0.10

            elif criticality == "medium":
                if row["open_24hr"] == 1:
                    bonus += 0.10
                if row["ambulance"] == 1:
                    bonus += 0.05

            # Facility level bonus (level 2=+0.05, level 3=+0.10, level 4=+0.15, level 5=+0.20)
            facility_level = row["facility_level"] or 1
            bonus += (facility_level - 1) * 0.05

            # Facility type bonus
            facility_type = row["facility_type"] or ""
            if criticality == "high" and facility_type in ("SDH", "DH"):
                bonus += 0.10
            elif facility_type == "RURAL_HOSPITAL":
                bonus += 0.05

            service_match_score = min(1.0, base_score + bonus)

            # --- Distance score ---
            distance_km = None
            phc_has_coords = (
                row["latitude"] is not None and row["longitude"] is not None
            )

            if has_patient_location and phc_has_coords:
                distance_km = haversine(
                    patient_lat, patient_lng,
                    row["latitude"], row["longitude"]
                )
                distance_score = max(0.0, 1.0 - (distance_km / MAX_DISTANCE_KM))
            else:
                distance_score = 0.0

            # --- Combined score ---
            if has_patient_location:
                combined_score = (
                    service_match_score * WEIGHT_SERVICE +
                    distance_score * WEIGHT_DISTANCE
                )
            else:
                combined_score = service_match_score

            recommendations.append({
                "id": row["id"],
                "name": row["name"],
                "block": row["block"],
                "address": row["address"],
                "contact": row["contact"],
                "open_24hr": bool(row["open_24hr"]),
                "timing": row["doctor_timing"] or "9AM–4PM Mon–Sat",
                "services": phc_services,
                "ambulance": bool(row["ambulance"]),
                "emergency_capable": bool(row["emergency_capable"]),
                "facility_level": facility_level,
                "facility_type": facility_type,
                "latitude": row["latitude"],
                "longitude": row["longitude"],
                "distance_km": distance_km,
                "service_match_score": service_match_score,
                "combined_score": combined_score,
                "matched_count": len(matched_services),
                "required_count": len(required_services),
            })

        conn.close()

        # --- Generate match reasons ---
        for r in recommendations:
            parts = []

            if r["required_count"] == 0:
                parts.append("Basic services available.")
            elif r["matched_count"] == r["required_count"]:
                parts.append(f"Matches {r['matched_count']}/{r['required_count']} required services.")
            elif r["matched_count"] > 0:
                parts.append(f"Partial match ({r['matched_count']}/{r['required_count']} services).")
            else:
                parts.append(f"Matches 0/{r['required_count']} required services.")

            if r["distance_km"] is not None:
                parts.append(f"{r['distance_km']:.1f} km away.")
            else:
                parts.append("Distance unavailable.")

            extra = []
            if r["emergency_capable"]:
                extra.append("Emergency capable")
            if r["open_24hr"]:
                extra.append("Open 24 hours")
            if r["ambulance"]:
                extra.append("Ambulance available")
            if extra:
                parts.append(". ".join(extra) + ".")

            r["match_reason"] = " ".join(parts)

            del r["matched_count"]
            del r["required_count"]
            del r["combined_score"]

        # --- Sort by combined score DESC ---
        recommendations.sort(key=lambda x: -(
            (x["service_match_score"] * WEIGHT_SERVICE) +
            (
                max(0.0, 1.0 - (x["distance_km"] / MAX_DISTANCE_KM)) * WEIGHT_DISTANCE
                if x["distance_km"] is not None and has_patient_location
                else 0.0
            )
        ))

        return recommendations[:5]

    except Exception as e:
        print(f"[recommend_phcs] Error: {e}")
        return []