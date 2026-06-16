# FitFindr — Starter Kit

This starter kit contains everything you need to begin Project 2.

## What's Included

```
ai201-project2-fitfindr-starter/
├── data/
│   ├── listings.json          # 40 mock secondhand listings
│   └── wardrobe_schema.json   # Wardrobe format + example wardrobe
├── utils/
│   └── data_loader.py         # Helper functions for loading the data
├── planning.md                # Your planning template — fill this out first
└── requirements.txt           # Python dependencies
```

## Setup

```bash
python3 -m pip install -r requirements.txt
```

Set your Groq API key in a `.env` file (get a free key at [console.groq.com](https://console.groq.com)):
```
GROQ_API_KEY=your_key_here
```

## The Mock Listings Dataset

`data/listings.json` contains 40 mock secondhand listings across categories (tops, bottoms, outerwear, shoes, accessories) and styles (vintage, y2k, grunge, cottagecore, streetwear, and more).

Each listing has: `id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, and `platform`.

Load it with:
```python3
from utils.data_loader import load_listings
listings = load_listings()
```

## The Wardrobe Schema

`data/wardrobe_schema.json` defines the format your agent uses to represent a user's existing wardrobe. It includes:

- `schema`: field definitions for a wardrobe item
- `example_wardrobe`: a sample wardrobe with 10 items you can use for testing
- `empty_wardrobe`: a starting template for a new user

Load an example wardrobe with:
```python3
from utils.data_loader import get_example_wardrobe
wardrobe = get_example_wardrobe()
```

## Where to Start

1. **Read `planning.md` and fill it out before writing any code.**
2. Verify the data loads correctly by running `python utils/data_loader.py`.
3. Build and test each tool individually before connecting them through your planning loop.

Your implementation files go in this same directory. There's no required file structure for your agent code — organize it however makes sense for your design.

## Tools

List every tool your agent will use. For each tool, fill in all four fields.
You must have at least 3 tools. The three required tools are listed — add any additional tools below them.

### Tool 1: search_listings

**What it does:**
This tool searches the mock secondhand listings dataset for clothing items that match the user’s request. It filters by size and price when provided, then ranks matching listings by how closely they match the item description.

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `description` (str): Keywords or short phrase describing the item the user wants, such as “vintage graphic tee”.
- `size` (str): Optional clothing or shoe size to filter listings by. If omitted, the tool searches across all sizes.
- `max_price` (float): Optional maximum price the user is willing to pay. If omitted, the tool does not apply a price filter.

**What it returns:**
Tool finds 3 matching listings, sorted by relevance.

**What happens if it fails or returns nothing:**
<!-- What should the agent do if no listings match? -->
If no listings match the description, size, and price filters, the tool returns an empty list. The agent should stop the flow, tell the user that no good matches were found, and optionally suggest broadening the query by changing the size, increasing the budget, or using a less specific description.

---

### Tool 2: suggest_outfit

**What it does:**
This tool takes the selected listing and the user’s wardrobe, then generates a styling suggestion that shows how the new item could be worn. If wardrobe items are available, it builds a specific outfit using pieces the user already owns; otherwise, it gives general styling advice.

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `new_item` (dict): The selected listing from search_listings, including details like title, description, category, style tags, price, and platform.
- `wardrobe` (dict): The user’s wardrobe data, usually containing an items list of clothing and accessories the agent can use when building an outfit suggestion.

**What it returns:**
<!-- Describe the return value -->
A short natural-language outfit suggestion. This may be a specific outfit using named wardrobe pieces or, if the wardrobe is empty, a general styling recommendation for how the item could be worn.

**What happens if it fails or returns nothing:**
<!-- What should the agent do if the wardrobe is empty or no outfit can be suggested? -->
If the wardrobe is empty, the tool should not fail. Instead, it should return general advice about what kinds of bottoms, shoes, layers, or accessories pair well with the new item. If it cannot generate a useful suggestion, the agent should return a fallback styling tip instead of ending the session.
---

### Tool 3: create_fit_card

**What it does:**
<!-- Describe what this tool does in 1–2 sentences -->
This tool turns the outfit suggestion and the selected listing into a short, social-style caption or “fit card.” It summarizes the look in a casual, expressive tone that feels like an outfit post rather than a product listing.

**Input parameters:**
<!-- List each parameter, its type, and what it represents -->
- `outfit` (str): The outfit suggestion generated by suggest_outfit, describing how the new item fits into a full look.


**What it returns:**
<!-- Describe the return value -->
A 2 to 4 sentence fit card caption that mentions the thrifted item naturally, includes the price and platform, and captures the overall vibe of the outfit.

**What happens if it fails or returns nothing:**
<!-- What should the agent do if the outfit data is incomplete? -->
If the outfit input is missing, empty, or too incomplete to turn into a caption, the tool should return a clear fallback message explaining that a fit card could not be created because no outfit suggestion was available. The agent should show the listing and outfit result if available, but skip the caption as the final step.

---

### Additional Tools (if any)

<!-- Copy the block above for any tools beyond the required three -->

---

## Planning Loop

**How does your agent decide which tool to call next?**
<!-- Describe the logic your planning loop uses. What does it look at? What conditions change its behavior? How does it know when it's done? -->

1. Parse user request into description, optional size, optional max_price, and optional wardrobe context.

2. If description is missing or blank, stop immediately and ask a clarification question ("What item are you looking for?"). Do not call any tools.

3. Call search_listings(description, size, max_price).

4. If search_listings errors, stop and return a fallback message ("I could not search listings right now. Please try again.").

5. If search_listings returns an empty list, stop and return "no matches" guidance with retry suggestions (broaden description, remove size filter, increase budget).

6. If results exist, set selected_item = results[0] and store backup_items = results[1:].

7. Call suggest_outfit(new_item=selected_item, wardrobe=wardrobe).

8. If suggest_outfit errors or returns empty text, set outfit_text to a generic fallback styling tip for selected_item and continue (do not stop).

9. If suggest_outfit succeeds, store the returned text in outfit_text.

10. Call create_fit_card(outfit=outfit_text, new_item=selected_item).

11. If create_fit_card errors or returns empty text, set fit_card = null and continue (do not stop).

12. If create_fit_card succeeds, store the returned caption in fit_card.

13. Build final response in this order: selected listing summary, outfit suggestion, optional fit card (only if fit_card is not null), optional backup listings.

14. Mark the run complete and end.

Completion rules:

- Early completion happens only on missing description, search tool failure, or no search results.
- Normal completion happens after attempting all three tools and assembling the final user response.
---

## State Management

**How does information from one tool get passed to the next?**
<!-- Describe how your agent stores and accesses state within a session. What data is tracked? How is it passed between tool calls? -->

The agent keeps a single session state object and updates it after each step in the planning loop.
Each tool reads from this state and writes its output back to it, so the next tool always gets structured, validated inputs.

Tracked state fields:

- user_request: original user message
- description: parsed item description
- size: optional parsed size filter
- max_price: optional parsed budget filter
- wardrobe: parsed or provided wardrobe context
- listings: full results from search_listings (possibly empty)
- selected_item: top listing from listings when available
- backup_items: remaining listings after the top result
- outfit_text: output from suggest_outfit, or fallback styling text
- fit_card: output from create_fit_card, or null if generation fails
- errors: list of tool errors encountered during the run
- status: one of waiting_for_input, searching, styling, captioning, complete, or failed
- stop_reason: set only when the loop ends early (missing_description, search_failed, no_results)

How data is passed between tools:

1. The planner parses the user input and stores description, size, max_price, and wardrobe in state.
2. search_listings reads description, size, and max_price, then writes listings.
3. The planner sets selected_item = listings[0] and backup_items = listings[1:] when listings exist.
4. suggest_outfit reads selected_item and wardrobe, then writes outfit_text (or fallback text).
5. create_fit_card reads outfit_text and selected_item, then writes fit_card (or null on failure).
6. The final response renderer reads selected_item, outfit_text, fit_card, and backup_items to assemble the user-facing output.

State rules:

- Only the planner mutates control fields like status and stop_reason.
- Tools are treated as pure functions: they return data; the planner is responsible for storing it.
- Early-stop conditions do not clear state; they preserve context for retries and clearer user feedback.
- If later tools fail, previously successful outputs remain in state so partial results can still be shown.


---

## Error Handling

For each tool, describe the specific failure mode you're handling and what the agent does in response.

| Tool | Failure mode | Agent response |
|------|-------------|----------------|
| search_listings | No results match the query | Stop the flow and return no-matches guidance: tell the user no listings were found and suggest retrying with a broader description, no size filter, or a higher budget. Set stop_reason = no_results. |
| suggest_outfit | Wardrobe is empty | Do not stop. Return general styling advice (e.g., what bottoms, shoes, or layers pair well with the item). Store the fallback text in outfit_text and continue to create_fit_card. |
| create_fit_card | Outfit input is missing or incomplete | Do not stop. Set fit_card = null and continue. Show the listing summary and outfit suggestion in the final response, but omit the caption step. |

---

## Architecture

<!-- Draw a diagram of your agent showing how the components connect:
     User input → Planning Loop → Tools (search_listings, suggest_outfit, create_fit_card)
                                                                          ↕
                                                                   State / Session
     Show what triggers each tool, how state flows between them, and where error paths branch off.
     ASCII art, a Mermaid diagram (https://mermaid.js.org/syntax/flowchart.html), or an embedded
     sketch are all fine. You'll share this diagram with an AI tool when asking it to implement
     the planning loop and each individual tool. -->

flowchart TD

U[User Input] --> P[Planning Loop]

P --> A[Parse request: description, size, max_price, wardrobe]
A --> B{Description present?}
B -->|No| C[Ask clarification question]
C --> END1([End: waiting_for_input])

B -->|Yes| D[Call search_listings(description, size, max_price)]
D --> E{Search error?}

E -->|Yes| F[Return fallback: could not search listings]
F --> END2([End: search_failed])

E -->|No| G{Any listings returned?}
G -->|No| H[Return no-matches guidance with retry suggestions]
H --> END3([End: no_results])

G -->|Yes| I[Set selected_item = listings[0]; backup_items = listings[1:]]
I --> J[Call suggest_outfit(new_item, wardrobe)]
J --> K{Outfit generated?}

K -->|No| L[Set fallback outfit_text and continue]
K -->|Yes| M[Store outfit_text]

L --> N[Call create_fit_card(outfit_text, selected_item)]
M --> N
N --> O{Fit card generated?}

O -->|No| Q[Set fit_card = null and continue]
O -->|Yes| R[Store fit_card]

Q --> T[Build final response]
R --> T
T --> V[Output order: listing summary, outfit suggestion, optional fit card, optional backup listings]
V --> END4([End: complete])

S[(State / Session)] --- P
S --- D
S --- J


STATE / SESSION (shared across steps)
-------------------------------------
user_request, description, size, max_price, wardrobe,
listings, selected_item, backup_items, outfit_text, fit_card,
errors, status, stop_reason

Notes:
- Planner controls status and stop_reason.
- Tools return data; planner writes state.
- Early-stop paths preserve state for retries.

---

## AI Tool Plan

<!-- For each part of the implementation below, describe:
     - Which AI tool you plan to use (Claude, Copilot, ChatGPT, etc.)
     - What you'll give it as input (which sections of this planning.md, your agent diagram)
     - What you expect it to produce
     - How you'll verify the output matches your spec before moving on

     "I'll use AI to help me code" is not a plan.
     "I'll give Claude my Tool 1 spec (inputs, return value, failure mode) and ask it to implement
     search_listings() using load_listings() from the data loader — then test it against 3 queries
     before trusting it" is a plan. -->

**Milestone 3 — Individual tool implementations:**
**Tool 1: search_listings()**
- **AI tool:** Claude (via Copilot)
- **Input:** I'll provide Claude with the Tool 1 spec (inputs: description, size, max_price; return value: 3 ranked listings; failure mode: empty list → agent should suggest retry), plus the listings.json schema and 5 sample listings from data/listings.json
- **Expected output:** A Python function that loads listings via load_listings() from utils/data_loader.py, filters by size/price, ranks by relevance to description, and returns top 3
- **Pytest verification:** Write tests for (1) "vintage graphic tee" query with size M and max_price 30 returns 3 results, (2) "oversized blazer" with no filters returns valid results, (3) query with no matches returns empty list — verify output format matches spec, ranking logic is sound, and empty list handling is correct. Tests shold go in the file /tests/test_tools.py

**Tool 2: suggest_outfit()**
- **AI tool:** Claude (via Copilot)
- **Input:** Tool 2 spec (inputs: new_item dict + wardrobe dict; return value: natural-language outfit suggestion; failure mode: empty wardrobe → return general advice), plus wardrobe_schema.json, 1 sample new_item, and 1 sample wardrobe with 5+ items
- **Expected output:** A Python function that accepts new_item and wardrobe, generates a specific outfit using named wardrobe pieces if available, or falls back to general styling advice if wardrobe is empty
- **verification:** Write tests for (1) populated wardrobe returns outfit mentioning specific pieces, (2) empty wardrobe returns general styling advice without crashing, (3) mismatched/unexpected item categories handled gracefully — verify output is natural language and function never raises exceptions. Tests shold go in the file /tests/test_tools.py

**Tool 3: create_fit_card()**
- **AI tool:** Claude (via Copilot)
- **Input:** Tool 3 spec (inputs: outfit string + new_item dict; return value: 2–4 sentence caption; failure mode: missing outfit → return fallback message), plus the outfit suggestions from Tool 2 and listing data structure
- **Expected output:** A Python function that accepts outfit text and new_item, produces a casual social-media-style caption mentioning price, platform, and vibe
- **verification:** Write tests for (1) complete outfit input returns 2–4 sentence caption with price/platform mentioned, (2) empty/None outfit returns clear fallback message, (3) missing listing fields handled gracefully — verify captions have correct tone and structure, and function never raises exceptions. Tests shold go in the file /tests/test_tools.py

**Milestone 4 — Planning loop and state management:**
- **AI tool:** Claude (via Copilot)
- **Input:** The complete Planning Loop section (steps 1–14), the State Management section (all tracked fields and data passing rules), the Architecture diagram, and a link to the Complete Interaction example; plus the three tool implementations from Milestone 3
- **Expected output:** A Python planner class/function that (1) parses user input into state fields, (2) implements the decision logic in Planning Loop steps 1–14 exactly as specified, (3) manages the 12 state fields (user_request, description, size, etc.) with proper updates after each tool call, (4) handles all three early-stop paths (missing description, search failed, no results), (5) calls all three tools in sequence when search succeeds, (6) assembles the final user response in the correct order (listing, outfit, fit card if exists, backup listings)
- **Verification:** Manually trace through the Complete Interaction example step by step: (1) user input "I'm looking for a vintage graphic tee under $30..." → verify parsing extracts description="vintage graphic tee", max_price=30, and wardrobe context; (2) verify search_listings is called with correct args → verify selected_item is set to top result; (3) verify suggest_outfit is called with selected_item and wardrobe; (4) verify create_fit_card is called with outfit_text and selected_item; (5) verify final response includes all four components in correct order with correct content; (6) test an error scenario (e.g., empty search results) and verify early-stop path is triggered correctly
---

## A Complete Interaction (Step by Step) - AI Usage Section

Write out what a full user interaction looks like from start to finish — tool call by tool call. Use a specific example query.
```
FitFindr must create a wardrobe for a user based off what the user is looking for. The user gives input as to what they are looking for, an outfit is suggested, and a matching "fit card" description is created for the outsit that is suggested.
```

**Example user query 1:** "I'm looking for a flowy emerald green midi dress under $75, size M. I usually wear ankle boots and a cropped denim jacket."

**Step 1:**
search_listings("emerald green midi dress", size="M", max_price=30.0) returns 3 matching listings sorted by relevance. Example Wardrobe radio button selected FitFindr picks the top result: "90s Silk Slip Dress — Floral, Midi Length, Depop, Good condition."

**Step 2:**
suggest_outfit(new_item=<silk slip dress>, wardrobe=<user's wardrobe>) returns: "You should totally pair the 90s silk slip dress with the black combat boots for a cool, edgy vibe. The flowy dress and the tough boots will create a nice contrast that's perfect for a casual day out. Throw on the vintage black denim jacket to add some extra edge and you're good to go."

**Step 3:**
create_fit_card(outfit=<suggestion>, new_item=<silk slip dress>) returns: "i just scored this amazing 90s silk slip dress on depop for $30 and i'm obsessed - the flowy, midi length is so perfect for a casual day out. i paired it with my black combat boots and vintage denim jacket for a cool, edgy vibe that's all about contrasts. the ivory and dusty pink florals on the dress add a touch of sweetness to the overall look, which i'm totally here for 🌸."

**Final output to user:**
Found a great match: 90s Silk Slip Dress — Floral, Midi Length ($30, Depop, Good condition).

How to style it with your wardrobe:
You should totally pair the 90s silk slip dress with the black combat boots for a cool, edgy vibe. The flowy dress and the tough boots will create a nice contrast that's perfect for a casual day out. Throw on the vintage black denim jacket to add some extra edge and you're good to go.

Alternatively, you could dress down the slip dress with the chunky white sneakers and the white ribbed tank top layered under the dress (just tie the tank top in a knot at the front to add some visual interest). This outfit would be super cute and relaxed, perfect for a weekend brunch or a stroll in the park. The ivory and dusty pink colors in the dress will look great with the crisp white sneakers and tank top.

Fit card caption:
 "i just scored this amazing 90s silk slip dress on depop for $30 and i'm obsessed - the flowy, midi length is so perfect for a casual day out. i paired it with my black combat boots and vintage denim jacket for a cool, edgy vibe that's all about contrasts. the ivory and dusty pink florals on the dress add a touch of sweetness to the overall look, which i'm totally here for 🌸."

 **Example user query 2:** "I'm looking for a sleek black blazer under $120, size M. I want something I can wear with wide-leg trousers and loafers for a polished work outfit."

**Step 1:**
search_listings("sleek black blazer", size="M/L", max_price=120.0) returns 3 matching listings sorted by relevance. Empty wardrobe selected. FitFindr picks the top result: "Wide-Leg Linen Trousers — Natural, poshmark, excellent condition."

**Step 2:**
suggest_outfit(new_item=<Wide-Leg Linen Trousers>, wardrobe=<new wardrobe>) returns: "These wide-leg linen trousers are perfect for a laid-back, summery look and pair well with sandals, slides, or sneakers. You can dress them up or down with a variety of tops, from cropped tanks to loose-fitting blouses, and add a denim jacket or cardigan for a cooler evening. The natural color also makes them a great match for earthy accessories like woven baskets, straw hats, or layered necklaces with natural stones. Overall, they'll fit right in with a cottagecore or minimalist wardrobe, evoking a effortless, warm-weather vibe."

**Step 3:**
create_fit_card(outfit=<suggestion>, new_item=<Wide-Leg Linen Trousers>) returns: "i just scored these wide-leg linen trousers on poshmark for $34 and i'm obsessed - they're giving me all the laid-back summer vibes, especially when i pair them with my fave sandals and a flowy top. i love how the natural color looks with my woven basket bag and layered necklaces. it's the perfect addition to my cottagecore wardrobe and i can already imagine wearing them on warm evenings with a denim jacket thrown over my shoulders 💛"

**Final output to user:**
Found a great match: Wide-Leg Linen Trousers — Natural, poshmark, ($34, poshmark, excellent condition).

How to style it with your wardrobe:
These wide-leg linen trousers are perfect for a laid-back, summery look and pair well with sandals, slides, or sneakers. You can dress them up or down with a variety of tops, from cropped tanks to loose-fitting blouses, and add a denim jacket or cardigan for a cooler evening. The natural color also makes them a great match for earthy accessories like woven baskets, straw hats, or layered necklaces with natural stones. Overall, they'll fit right in with a cottagecore or minimalist wardrobe, evoking a effortless, warm-weather vibe.