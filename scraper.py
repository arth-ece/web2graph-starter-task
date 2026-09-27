import requests ## for accessing webpages via HTTPS: ##
import xml.etree.ElementTree as ET ## for parsing xml files from the REST API offered by the nps website into navigatable trees ##
import json ## to turn python lists and dicts into json graphs ##
import re ## using regex to pull out park id from website links ##
import time ## delay request times by 0.5s for handling requests when creating my json ##
import os ## for reading the NPS API key from the environment ##
from dotenv import load_dotenv ## loads variables from .env into the environment ##
from bs4 import BeautifulSoup ## for parsing HTML webpages, similar to ET ##

load_dotenv() ## reads my .env file and looks for api key-value ##
NPS_API_KEY = os.getenv("NPS_API_KEY")
if not NPS_API_KEY:
    raise RuntimeError(
        "NPS_API_KEY not found. Create a .env file with NPS_API_KEY=your_key_here. "
        "Get a free key at https://www.nps.gov/subjects/developer/get-started.htm"
    )

OTHER_PARK_ID_RE = re.compile(r"(\d+)\s*$") ## variable that compiles any sequence of characters that are continuous digits at the end of a string with or without whitespace at the end of it ##

## this function ensures whenever yoy input a park name, it will pull the 4 letter code associated with the park ##
def get_park_code(park_name):
    response = requests.get(
        "https://developer.nps.gov/api/v1/parks",
        params={"q": park_name, "api_key": NPS_API_KEY} ## ensuring that the program can access the current park name in the for loop with the users api key ##
    )
    data = response.json()
    for park in data["data"]: ## iterating through the park data looking for the full name of the current park ##
        if park["fullName"].lower() == park_name.lower(): 
            return park["parkCode"].upper() ## if the park found in the data is equal to the park inputted, then the program will use the 4 letter code for that park, this ensures that there is a 4 letter code associated with every park when building the json graph ##
    return None


## function to help with formatting "native" values from the webpages. Making sure that it's consistently "Native" or "Non-Native" rather than "NATIVE" or "non-native" ##
def normalize_nativeness(raw):
    if not raw:
        return "Unknown"
    normalized = raw.strip().lower()
    if normalized == "native": ## conditional that turns a lowercase "native" into an uppercase "Native" to match the json i created manually"
        return "Native"
    if normalized == "non-native": ## same conditional with "non-native" turning to "Non-Native" ##
        return "Non-Native"
    return "Unknown"

## function to pull the value of each category for each species (occurrence, nativeness, etc.) ##
def get_field_value(container, label_text):
    label = container.find("div", class_="fakeLabel-R180", string=label_text) ## if the program can find a class of the HTMl that is "fakeLabel-R180" and that matches label_text (occurrence, nativeness, etc.), then the workflow continues ##
    if label is None:
        return None
    value_div = label.find_next_sibling("div", class_="formCell") ## searches for the value of the label if there is one (Present for Occurrence would be an example) ##
    if value_div is None:
        return None
    return value_div.get_text(strip=True) ## returns whatever value and removes any whitespace ##


## builds the species/park graph for any park name + species category, resolving the park's NPS unit code dynamically ##
def build_species_graph(park_name: str, category: str) -> dict:
    unit_code = get_park_code(park_name)
    if unit_code is None:
        raise ValueError(f"Could not find NPS unit code for park name: {park_name}")

    ## accessing REST API from nps.gov ##
    response = requests.get(f"https://irmaservices.nps.gov/NPSpecies/v3/rest/detaillist/{unit_code}/{category}")

    ## parsing xml file into navigatable tree for my program ##
    species_data = ET.fromstring(response.text)

    items = species_data.findall("SpeciesListItem")
    results = []
    nodes = [] ## creating node that'll include all parks and all species present in the target park ##
    edges = [] ## creating edge list for all connections from species present in the target park to species present in all other parks ##

    ## Loop to determine if the species is actually present in the target park ##
    for item in items:
        occurrence_value = item.find("Occurrence").text
        if occurrence_value == "Present":
            results.append(item)

    nodes.append({"value": park_name, "type": "Park"})
    known_park_values = {park_name}

    ## developing node and edge values for species by including scientific name, order, family, common names, and native status specifically from the XML file i found from the REST API ##
    for item in results:
        order = item.find("Order").text
        scientific_name = item.find("ScientificName").text
        family = item.find("Family").text
        common_names = item.find("CommonNames").text
        common_names_list = common_names.split(", ")
        nativeness = item.find("Nativeness").text
        if nativeness.lower() == "non-native":
            nativeness = "Non-Native"
        species_id = item.find("Id").text
        node = {
            "value": scientific_name,
            "type": "Species",
            "order": order,
            "family": family,
            "common_names": common_names_list
        }
        edge = {
            "source": scientific_name,
            "destination": park_name,
            "type": "present_in",
            "native_status": nativeness
        }
        nodes.append(node)
        edges.append(edge)

        ## fetching and parsing species via species id from nps.gov html via BeautifulSoup ##
        print(f"Fetching other parks for {scientific_name} in {park_name}...")
        time.sleep(0.5)
        try:
            profile_response = requests.get(f"https://irma.nps.gov/NPSpecies/Species/Profile/{species_id}")
            profile_soup = BeautifulSoup(profile_response.text, "html.parser") ## the BeautifulSoup library takes the raw html from profile_response.text and turns it into navigatable text via its built-in html parser ##
        except requests.RequestException as e:
            print(f"  Warning: failed to fetch profile {species_id} for {scientific_name}: {e}")
            continue

        other_parks_div = profile_soup.find("div", id="otherparks") ## search for ids in the html file that are listed as "other parks" ##
        other_parks = [] ## create empty list to input park id and park name ##
        if other_parks_div is not None:
            for link in other_parks_div.find_all("a"): ## find links in other parks ##
                match = OTHER_PARK_ID_RE.search(link.get("href", "")) ## use regex to pull out the digits in the end of the string that are continuous ##
                if match is None:
                    continue
                other_parks.append((match.group(1), link.get_text(strip=True))) ## add park id and park name into the empty list ##

        for other_id, other_park_name in other_parks: ## nested for loop going through the list i created with the park id and then the park name ##
            print(f"  Checking {other_park_name}...") ## going through each park ##
            time.sleep(0.5) ## rate-limiting ##
            try:
                other_response = requests.get(f"https://irma.nps.gov/NPSpecies/Species/Profile/{other_id}") ## fetching the park website for each park in other_parks ##
                other_soup = BeautifulSoup(other_response.text, "html.parser")  ## parsing website from other park from raw html into navigatable code ##
            except requests.RequestException as e:
                print(f"    Warning: failed to fetch profile {other_id} for {other_park_name}: {e}")
                continue

            attributes_div = other_soup.find("div", id="attributes") ## searching for an id in the html file named "attributes" ##
            if attributes_div is None: ## if the scraper can somehow not find any section named attributes, just ignore that and continue ##
                continue

            other_occurrence = get_field_value(attributes_div, "Occurrence") ## searching within the attributes id for a value called "Occurence" which will give whether the animal is present, probably present, or not present ##
            if other_occurrence != "Present":
                continue

            other_nativeness = normalize_nativeness(get_field_value(attributes_div, "Nativeness")) ## first, pulling the value of nativeness from the attributes_div id, then using the nromalize_nativeness function I created to make sure that the formatting of the string is consistent ##

            if other_park_name not in known_park_values: ## adding new nodes for parks and making sure that each node is unique by adding the other park name to the known_park_values variable that we created earlier ##
                nodes.append({"value": other_park_name, "type": "Park"}) ## adding the other park to node ##
                known_park_values.add(other_park_name) ## adding other park to list with known parks ##

            edges.append({ ## adding scientific name, park name, present status, then nativeness status with each iteration of the for loop ##
                "source": scientific_name,
                "destination": other_park_name,
                "type": "present_in",
                "native_status": other_nativeness
            })

    return {"nodes": nodes, "edges": edges}


## runs the same validation checks as before against a built graph, returning the list of error strings (empty if none) ##
def validate_graph(graph: dict) -> list:
    nodes = graph["nodes"]
    edges = graph["edges"]

    validation_errors = []
    node_values_seen = []
    for node in nodes:
        if not node.get("value") or not node.get("type"): ## this helps to show if the key is completely absent or if it exists but has no value ##
            validation_errors.append(f"Node missing value/type: {node}") ## error gets appended into the validation errors list ##
        node_values_seen.append(node.get("value"))

    duplicate_values = {v for v in node_values_seen if node_values_seen.count(v) > 1} ## checks to see for any duplicates in the nodes ##
    if duplicate_values:
        validation_errors.append(f"Duplicate node values found: {duplicate_values}") ## gives error message if there is a duplicate found ##

    node_values_set = set(node_values_seen)
    for edge in edges:
        if edge["source"] not in node_values_set: ## this is for the animals ##
            validation_errors.append(f"Edge source not found in nodes: {edge}") ## if a value in the edge list is not found in the node list, then this is an error because how can there be a connection if the node value does not even exist ##
        if edge["destination"] not in node_values_set: ## this is for the parks ##
            validation_errors.append(f"Edge destination not found in nodes: {edge}") ## if a edge value for a park is not found in the node, then that means the scraper did something wrong for the same reason mentioned. There cannot be a value in the edge if that same value is not represented in the node ##

    return validation_errors


## builds, validates, prints a summary for, and saves a single park/category graph ##
def run_and_save(park_name: str, category: str, output_path: str) -> None:
    print(f"=== {park_name} / {category} ===")

    graph = build_species_graph(park_name, category)
    validation_errors = validate_graph(graph)

    if validation_errors: ## if there is anything in the validation_errors list, then the program will output "Validation FAILED"
        print("Validation FAILED:")
        for error in validation_errors:
            print(f"  - {error}") ## outputs whatever the actual error(s) was in the list ##
    else:
        print("Validation passed: all nodes and edges are well-formed.") ## if nothing is in the list, that means there was no errors, so the makeup of the json is correct ##

    nodes = graph["nodes"]
    edges = graph["edges"]
    species_node_count = sum(1 for n in nodes if n["type"] == "Species") ## sum of all species in the node class ##
    park_node_count = sum(1 for n in nodes if n["type"] == "Park") ## sum of all parks in the node class ##
    print(f"Total nodes: {len(nodes)} (Species: {species_node_count}, Park: {park_node_count})") ## prints out all nodes, then the amount of species, then the number of parks ##
    print(f"Total edges: {len(edges)}") ## prints out the amount of edges ##

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(graph, f, indent=2, ensure_ascii=False) ## writes the node and edge lists to the given output file ##
    print()


if __name__ == "__main__":
    run_and_save("Acadia National Park", "Amphibian", "graphs/acadia_amphibians.json") ## running scraper simulation for ACAD amphibians ##
    run_and_save("Badlands National Park", "Reptile", "graphs/badlands_reptiles.json") ## running scraper simulations for Badlands National Park Reptiles ##
