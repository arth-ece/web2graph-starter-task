# NPSpecies Knowledge Graph Scraper

Given a park name and an animal category, this scraper builds a knowledge graph of every species in that category that is currently "Present" in the park. It then connects each species to every other park where it is also "Present", and records whether NPS marks it as native or non-native in each of those parks.

## Setup

1. Create and activate a virtual environment:

```powershell
   python -m venv .venv
   .venv\Scripts\Activate.ps1
```

2. Install dependencies:

```powershell
   pip install -r requirements.txt
```

3. Get a free NPS API key at https://www.nps.gov/subjects/developer/get-started.htm, then create a `.env` file in the project root containing:

```
   NPS_API_KEY=your_api_key
```

   The key is only used to look up a park's 4-letter unit code from its name (e.g. "Acadia National Park" -> `ACAD`). The script stops with a clear error if the key is missing.

## Usage

to generate one graph for a single park and category, run this in your terminal:

```
python scraper.py "Badlands National Park" reptiles
```

This saves to `graphs/<park>_<category>_scraped.json` by default.

To choose the output file:

```powershell
python scraper.py "Badlands National Park" reptiles -o graphs/out.json
```

This builds the graph for reptiles in Badlands National Park and saves it to `graphs/out.json`.

To generate all three graphs required by the task, run the script with no arguments:

```powershell
python scraper.py
```

This writes `graphs/acadia_reptiles.json`, `graphs/acadia_amphibians.json`, and `graphs/badlands_reptiles.json`.

**Note:** the park name must match NPS's full park name (capitalization is ignored). "Badlands National Park" works, but "Badlands" alone does not.

## Graph schema

Every graph has the form `{"nodes": [...], "edges": [...]}` and uses the same schema throughout.

**Species node**

```json
{"value": "Diadophis punctatus", "type": "Species", "order": "Squamata", "family": "Colubridae", "common_names": ["Northern Ringneck Snake", "Ringneck Snake", "Ring-necked Snake"]}
```

The NPS scientific name is the node's identity. `common_names` is always a list.

**Park node**

```json
{"value": "Shenandoah National Park (SHEN)", "type": "Park"}
```

The starting park uses the name you passed in. Other parks use the name exactly as NPS lists it, including the code in parentheses.

**Edge**

```json
{"source": "Diadophis punctatus", "destination": "Shenandoah National Park (SHEN)", "type": "present_in", "native_status": "Native"}
```

`native_status` is `Native`, `Non-Native`, or `Unknown`.

**Design choices**

- i decided to put the native status on the edges because an animal can be native in one park but not the other, so it makes sense put this categorization in the edge section.
- I decided to only include parks that had the label "Present", anything with "Probably Present" was not included in generating species nodes.
- Each park has exactly one node, however many species connect to it.

## How the scraper works

1. Use the API Key from the developer nps website to ensure that the program relates each park name to a 4-letter code
2. Use the rest API to search through each species and add them to the node list only if "Occurrence" == Present
3. Parse the HTML file for each species via species ID and look for the "Other Parks" section, where the scraper will cycle through each of the other parks and then determine if "Occurrence" == Present and the nativeness. 
4. Use the "Other Parks" list at the bottom of the html to add the park names to the nodes and then create edges with the species name as the source and then the park name as the destination, also including the nativeness. 
5. Build the graph with this logic then ensure that the graph has all unique node values, no empty fields, and every edge endpoint matches a node, then write the JSON file for the graph. 

The REST API is used wherever possible because structured output is more reliable than parsing HTML. It has no species-to-parks lookup, so steps 3 and 4 parse the profile pages instead. Requests are spaced 0.5 seconds apart.

## Results

| Graph | Species | Parks | Edges |
|---|---|---|---|
| Acadia reptiles | 7 | 145 | 308 |
| Acadia amphibians | 11 | 151 | 493 |
| Badlands reptiles | 6 | 156 | 274 |

## Manual vs. scraped (Acadia reptiles)

I built `acadia_reptiles.json` by hand first, then ran the scraper on the same
input. The scraper found 14 species-park edges I had missed (12 for
*Chelydra serpentina*, 2 for *Thamnophis sirtalis*) and showed one status I had
entered wrong (*Chrysemys picta* at Katahdin Woods and Waters is "Unknown", not
"Native"). I checked all of these against NPS's own records, corrected the manual
file, and confirmed the two graphs now match exactly (152 nodes, 308 edges).
