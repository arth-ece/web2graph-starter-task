# NPSpecies Knowledge Graph Scraper

When you feed this scraper a park name and an animal category, it will generate a knowledge graph containing every animal under that animal category present in the park given, then it will create connections between those same animals in other parks as well, given that they are present. The scraper will also provide whether the animal is native or non-native in each park that they are present including and excluding the park name given. 
## Setup

1. create and activate your virtual environment:

```powershell
   python -m venv .venv
   .venv\Scripts\Activate.ps1
```

2. Install dependencies:

```powershell
   pip install -r requirements.txt
```

3. you need to get an NPS API key to ensure that the scraper can associate a 4-letter code to the park name that you inputted, get this API key at https://www.nps.gov/subjects/developer/get-started.htm, then create a `.env` file in the project root containing:

```
   NPS_API_KEY=your_api_key
```
if the key is not found, there will be a key error. The OS library is what helps with your scraper scanning your .env file and finding the API key. 

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

this will build a graph of all reptiles present in the Badlands National Park and then save it to `graphs/out.json`.

To generate all three graphs required by the task, run the script with no arguments, running this will also override the manual JSON graph of acadia_reptiles.json that I created, which is fine because the scraped version will be the exact same as the manual version:

```powershell
python scraper.py
```

This writes `graphs/acadia_reptiles.json`, `graphs/acadia_amphibians.json`, and `graphs/badlands_reptiles.json`.

**Note:** the park name you input must match the name of the park on the NPS website, capitalization does not matter though.

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

- I decided to put native_status in the edges only because a species can be native in one park but not the other. The status should belong to the species-park pair. 
- I only included Park occurrence when "Occurrence" was exactly "Present". If it was anything else, even "Probably Present", I did not include it in my node.
- Each park has exactly one node, however many species connect to it.

## How the scraper works

1. Use the API Key from the developer nps website to ensure that the program relates each park name to a 4-letter code
2. Use the rest API to search through each species and add them to the node list only if "Occurrence" == Present and add an edge from the species to the starting park with its nativeness there
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
"Native"). I checked the NPS data with all of these, corrected the manual
file, and confirmed the two graphs now match exactly (152 nodes, 308 edges).
