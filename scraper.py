import requests
import xml.etree.ElementTree as ET

response = requests.get("https://irmaservices.nps.gov/NPSpecies/v3/rest/detaillist/ACAD/Reptile")

reptile_data = ET.fromstring(response.text)

items = reptile_data.findall("SpeciesListItem")
results = []
nodes = []
edges = []
for item in items:
    occurrence_value = item.find("Occurrence").text
    if occurrence_value == "Present":
        results.append(item)

nodes.append({"value": "Acadia National Park", "type": "Park"})

for item in results:
    order = item.find("Order").text
    scientific_name = item.find("ScientificName").text
    family = item.find("Family").text
    common_names = item.find("CommonNames").text
    common_names_list = common_names.split(", ")
    nativeness = item.find("Nativeness").text
    if nativeness.lower() == "non-native":
        nativeness = "Non-Native"
    node = {
        "value": scientific_name,
        "type": "Species",
        "order": order,
        "family": family,
        "common_names": common_names_list
    }
    edge = {
        "source": scientific_name,
        "destination": "Acadia National Park",
        "type": "present_in",
        "native_status": nativeness
    }
    nodes.append(node)
    edges.append(edge)
profile_response = requests.get("https://irma.nps.gov/NPSpecies/Species/Profile/321904")
print(profile_response.text)