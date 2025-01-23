GRAPH_FIELD_SEP = "<SEP>"
AGG_CHUNK_SEP = "<CID>"
SUBGRAPH_SEP = "<SG>"
PROMPTS = {}

PROMPTS["ORGANIZATION"] = "Zoominfo"
PROMPTS["DEFAULT_LANGUAGE"] = "English"
PROMPTS["DEFAULT_TUPLE_DELIMITER"] = "<|>"
PROMPTS["DEFAULT_RECORD_DELIMITER"] = "##"
PROMPTS["DEFAULT_COMPLETION_DELIMITER"] = "<|COMPLETE|>"
PROMPTS["process_tickers"] = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
PROMPTS["DEFAULT_ENTITY_TYPES"] = ["organization", "product_line", "product_sku", "feature", "security", "sme", "use_case"]
PROMPTS["known_entities"] = """Here are some pre known entities of {organization} that may appear in the text. Use these details to unify them with any mentions in the text. If additional information about these entities is found, merge it into the description. If you encounter new entities not listed here, capture them separately using the same entity_type conventions.
#############################
-Known Entities-
#############################
{known_entities}"""
PROMPTS["entity_extraction"] = """-Goal-
Given {organization}'s (organization) data, identify all entities that match the given entity types and then identify relationships among them. Note that {organization}'s data may also include mentions of other organizations (e.g., partners, clients, competitors in testimonials or customer success stories). These other organizations should also be captured with the entity type "organization."
Use {language} as the output language.

{known_entities}

-Important Note- 
**The following list of primary entity types is not exhaustive. Always remain attentive to any additional, well-defined entities (e.g., locations, concepts, roles, events, process, etc.) that may appear in the text. If you encounter an entity type that is not covered by the primary list, create a new, descriptive label for it (e.g., "location" or "concept") and include it in your entity extraction.**

-Entity Types and Definitions-
- organization: Any company/organization (including {organization} itself and any other referenced organizations)
- product_line: A category of products solving specific business needs, often organized by functionality or purpose.
- product_sku: A specific version or tier within a product line, with unique features or pricing.
- feature: Functionalities or tools within a product (or product line/product sku) that address specific customer problems.
- security: Details about security features, standards, or compliance certifications related to the product.
- sme: Subject matter experts (roles or individuals) who provide expertise or guidance on product areas.
- use_case: Real-world applications of the product to solve specific business problems or achieve specific outcomes.

-Steps-
1. Identify all entities. For each identified entity, extract the following information:
- entity_name: Name of the entity. If English, capitalize proper nouns.
- entity_type: One of the following types: [{entity_types}]
- entity_description: A comprehensive description summarizing the entity's key attributes, role, or purpose, based on the given text.
Format each entity as ("entity"{tuple_delimiter}<entity_name>{tuple_delimiter}<entity_type>{tuple_delimiter}<entity_description>)

2. Identify all pairs of entities that are clearly related. For example:
   - An organization might include multiple product_lines
   - A product_line might include multiple product_skus.
   - A product_sku might incorporate certain features.
   - A feature might be relevant to specific use cases.
   - A product_line or product_sku might have associated security details.
   - An sme might be associated with certain product lines or features.
   - A use_case might relate to a product_line, product_sku, or feature.
   
For each pair of related entities, extract:
- source_entity: name of the source entity (from step 1)
- target_entity: name of the target entity (from step 1)
- relationship_description: explanation of why these entities are related
- relationship_strength: a numeric score indicating the strength of the relationship (1-10)
- relationship_keywords: key words that summarize the nature of the relationship
Format each relationship as ("relationship"{tuple_delimiter}<source_entity>{tuple_delimiter}<target_entity>{tuple_delimiter}<relationship_description>{tuple_delimiter}<relationship_keywords>{tuple_delimiter}<relationship_strength>)

3. Identify high-level keywords that summarize the main concepts or topics of the entire text.
Format as ("content_keywords"{tuple_delimiter}<high_level_keywords>)

4. Return output in {language} as a single list of all entities and relationships identified, using **{record_delimiter}** as the list delimiter.

5. When finished, output {completion_delimiter}

#############################
-Examples-
#############################
{examples}

#############################
-Real Data-
#############################
Entity_types: {entity_types}
Text: {input_text}
#############################
Output:
"""

PROMPTS["entity_extraction_examples"] = [
    """Example 1:
Entity_types: [organization, product_line, product_sku, feature, security, sme, use_case]
Text:
"HubSpot, Inc. is an American developer and marketer of software products for inbound marketing, sales, and customer service. It offers Marketing, Sales, and Service Hubs for different teams. The Marketing Hub Professional plan includes advanced analytics and A/B testing. The Service Hub Manager specializes in customer support workflows and tool integrations. One e-commerce company used the Marketing Hub to increase customer retention by 20% through personalized email campaigns. HubSpot complies with GDPR, ensuring secure handling of customer data."

################
Output:
("entity"{tuple_delimiter}"Hubspot"{tuple_delimiter}"organization"{tuple_delimiter}"American organization providing marketing, sales, and customer services"){record_delimiter}
("entity"{tuple_delimiter}"Marketing Hub"{tuple_delimiter}"product_line"{tuple_delimiter}"A product line from HubSpot focused on marketing solutions."){record_delimiter}
("entity"{tuple_delimiter}"Sales Hub"{tuple_delimiter}"product_line"{tuple_delimiter}"A product line from HubSpot focused on sales enablement."){record_delimiter}
("entity"{tuple_delimiter}"Service Hub"{tuple_delimiter}"product_line"{tuple_delimiter}"A product line from HubSpot focused on customer service and support."){record_delimiter}
("entity"{tuple_delimiter}"Marketing Hub Professional"{tuple_delimiter}"product_sku"{tuple_delimiter}"A specific paid tier of the Marketing Hub offering advanced analytics and A/B testing."){record_delimiter}
("entity"{tuple_delimiter}"Advanced Analytics"{tuple_delimiter}"feature"{tuple_delimiter}"A feature within Marketing Hub Professional that provides in-depth performance insights."){record_delimiter}
("entity"{tuple_delimiter}"A/B Testing"{tuple_delimiter}"feature"{tuple_delimiter}"A feature in Marketing Hub Professional that allows testing different strategies to optimize results."){record_delimiter}
("entity"{tuple_delimiter}"Service Hub Manager"{tuple_delimiter}"sme"{tuple_delimiter}"A subject matter expert specializing in customer support workflows and tool integrations within the Service Hub."){record_delimiter}
("entity"{tuple_delimiter}"GDPR Compliance"{tuple_delimiter}"security"{tuple_delimiter}"A security and compliance standard ensuring proper handling of customer data."){record_delimiter}
("entity"{tuple_delimiter}"Increased Customer Retention via Personalized Emails"{tuple_delimiter}"use_case"{tuple_delimiter}"A real-world application of the Marketing Hub to enhance customer retention through targeted email campaigns."){record_delimiter}

("relationship"{tuple_delimiter}"Hubspot"{tuple_delimiter}"Marketing Hub"{tuple_delimiter}"Hubspot offer Marketing hub."{tuple_delimiter}"marketing"{tuple_delimiter}9){record_delimiter}
("relationship"{tuple_delimiter}"Hubspot"{tuple_delimiter}"Service Hub"{tuple_delimiter}"Hubspot offers service hub."{tuple_delimiter}"service"{tuple_delimiter}9){record_delimiter}
("relationship"{tuple_delimiter}"Hubspot"{tuple_delimiter}"Sales Hub"{tuple_delimiter}"Hubspot offers sales hub."{tuple_delimiter}"sales"{tuple_delimiter}9){record_delimiter}
("relationship"{tuple_delimiter}"Marketing Hub"{tuple_delimiter}"Marketing Hub Professional"{tuple_delimiter}"The Marketing Hub Professional is a specific SKU within the Marketing Hub product line."{tuple_delimiter}"product hierarchy, tiered offering"{tuple_delimiter}9){record_delimiter}
("relationship"{tuple_delimiter}"Marketing Hub Professional"{tuple_delimiter}"Advanced Analytics"{tuple_delimiter}"Advanced Analytics is a feature included in the Marketing Hub Professional SKU."{tuple_delimiter}"feature inclusion"{tuple_delimiter}8){record_delimiter}
("relationship"{tuple_delimiter}"Marketing Hub Professional"{tuple_delimiter}"A/B Testing"{tuple_delimiter}"A/B Testing is another feature included in the Marketing Hub Professional SKU."{tuple_delimiter}"feature inclusion"{tuple_delimiter}8){record_delimiter}
("relationship"{tuple_delimiter}"Service Hub"{tuple_delimiter}"Service Hub Manager"{tuple_delimiter}"The Service Hub Manager is an SME associated with the Service Hub product line."{tuple_delimiter}"expert association"{tuple_delimiter}7){record_delimiter}
("relationship"{tuple_delimiter}"HubSpot"{tuple_delimiter}"GDPR Compliance"{tuple_delimiter}"HubSpot complies with GDPR, a security standard."{tuple_delimiter}"compliance, security standard"{tuple_delimiter}9){record_delimiter}
("relationship"{tuple_delimiter}"Marketing Hub"{tuple_delimiter}"Increased Customer Retention via Personalized Emails"{tuple_delimiter}"The Marketing Hub enabled a use case that improved customer retention."{tuple_delimiter}"practical application, customer retention"{tuple_delimiter}10){record_delimiter}
("content_keywords"{tuple_delimiter}"product lines, SKUs, features, SMEs, security compliance, use cases"){completion_delimiter}
#############################""",
]

PROMPTS["summarize_entity_descriptions"] = """You are a helpful assistant responsible for generating a comprehensive summary of the data provided below.
Given one or two entities, and a list of descriptions, all related to the same entity or group of entities.
Please concatenate all of these into a single, comprehensive description. Include all relevant details and resolve any contradictions.
Use {language} as output language.

#######
-Data-
Entities: {entity_name}
Description List: {description_list}
#######
Output:
"""

PROMPTS["entiti_continue_extraction"] = """Some entities were missed in the last extraction. Add them below using the same format:
"""

PROMPTS["entiti_if_loop_extraction"] = """Check if some entities are still missing from the previous extraction. Answer YES or NO:
"""

PROMPTS["fail_response"] = "Sorry, I'm not able to provide an answer to that question."

PROMPTS["rag_response"] = """---Role---

You are a helpful assistant for ZoomInfo, responding to questions about their data in the tables provided. 
Your answers must strictly rely on the provided context. Do not hallucinate or invent any information 
beyond what is supported by the data tables.

---Goal---

Generate a response of the target length and format that accurately addresses the user's question. 
Summarize all relevant information in the input data tables according to the requested response 
length and format. Incorporate any pertinent general knowledge only if it directly supports 
the provided data. If you don't know the answer from the context, say so without making anything up. 
Omit any information that lacks supporting evidence in the data tables.

When handling relationships with timestamps:
1. Each relationship has a "created_at" timestamp indicating when we acquired this knowledge.
2. If conflicting relationships exist, consider both the semantic content and the timestamp.
3. Do not automatically prefer the most recently created relationships; use contextual judgment.
4. For time-specific queries, prioritize temporal information in the content before considering creation timestamps.

---Target response length and format---

{response_type}

---Data tables---

{context_data}

Add sections and commentary to the response as appropriate for the length and format. 
Style the response in markdown, and refrain from providing any information not grounded in the data."""


PROMPTS["keywords_extraction"] = """---Role---

You are a helpful assistant tasked with identifying both high-level and low-level keywords in the user's query.

---Goal---
Given the query, list both high-level and low-level keywords. High-level keywords focus on overarching concepts or themes, while low-level keywords focus on specific entities, details, or concrete terms.

----Instructions----
Evaluate the query to understand its intent and scope and extract high level and low level keywords that are highly relevant to the query.

### Output Format:
- Output the keywords in JSON format.
- The JSON should have two keys:
  - "high_level_keywords" for overarching concepts or themes.
  - "low_level_keywords" for specific entities or details.

######################
-Examples-
######################
{examples}

#############################
-Real Data-
######################
Query: {query}
######################
The `Output` should be human text, not unicode characters. Keep the same language as `Query`.
Output:

"""

PROMPTS["keywords_extraction_examples"] = [
    """Example 1:

Query: "In Docket, does RFP and QnA have different data pipelines?"
################
Output:
{
"high_level_keywords": ["Docket", "Data pipelines", "RFP", "QnA"],
"low_level_keywords": ["Pipeline architecture", "RFP processes", "QnA processes", "Data segregation"]
}
################

Example 2:

Query: "What are Slack's data retention policies compared to Docket's 90-day message retention?"
################
Output:
{
"high_level_keywords": ["Slack", "Docket", "Data retention policies"],
"low_level_keywords": ["90-day retention", "Message deletion", "Data storage compliance", "Retention"]
}
################

Example 3:

Query: "How should I respond to a customer that's concerned about keeping their data safe?"
################
Output:
{
"high_level_keywords": ["Customer concerns", "Data safety", "Security measures"],
"low_level_keywords": ["Encryption", "Data privacy", "Compliance standards", "Customer assurance"]
}
################

Example 4:

Query: "How can a customer be certain Docket doesn't use our data to train? Any proof vs just contractual agreement?"
################
Output:
{
"high_level_keywords": ["Docket", "Data usage", "Customer trust", "Training models"],
"low_level_keywords": ["Proof of compliance", "Contractual guarantees", "Data integrity", "Privacy assurance"]
}
################

Example 5:

Query: "How does Docket work if it doesn't train on customer data?"
################
Output:
{
"high_level_keywords": ["Docket", "Training models", "Customer data"],
"low_level_keywords": ["Alternative models", "Data-independent operations", "Privacy"]
}
################""",
]

PROMPTS["naive_rag_response"] = """---Role---

You are a helpful assistant responding to questions about documents provided.


---Goal---

Generate a response of the target length and format that responds to the user's question, summarizing all information in the input data tables appropriate for the response length and format, and incorporating any relevant general knowledge.
If you don't know the answer, just say so. Do not make anything up.
Do not include information where the supporting evidence for it is not provided.

When handling content with timestamps:
1. Each piece of content has a "created_at" timestamp indicating when we acquired this knowledge
2. When encountering conflicting information, consider both the content and the timestamp
3. Don't automatically prefer the most recent content - use judgment based on the context
4. For time-specific queries, prioritize temporal information in the content before considering creation timestamps

---Target response length and format---

{response_type}

---Documents---

{content_data}

Add sections and commentary to the response as appropriate for the length and format. Style the response in markdown.
"""

PROMPTS[
    "similarity_check"
] = """Please analyze the similarity between these two questions:

Question 1: {original_prompt}
Question 2: {cached_prompt}

Please evaluate the following two points and provide a similarity score between 0 and 1 directly:
1. Whether these two questions are semantically similar
2. Whether the answer to Question 2 can be used to answer Question 1
Similarity score criteria:
0: Completely unrelated or answer cannot be reused, including but not limited to:
   - The questions have different topics
   - The locations mentioned in the questions are different
   - The times mentioned in the questions are different
   - The specific individuals mentioned in the questions are different
   - The specific events mentioned in the questions are different
   - The background information in the questions is different
   - The key conditions in the questions are different
1: Identical and answer can be directly reused
0.5: Partially related and answer needs modification to be used
Return only a number between 0-1, without any additional content.
"""

PROMPTS["mix_rag_response"] = """---Role---

You are a professional assistant responsible for answering questions based on knowledge graph and textual information. Please respond in the same language as the user's question.

---Goal---

Generate a concise response that summarizes relevant points from the provided information. If you don't know the answer, just say so. Do not make anything up or include information where the supporting evidence is not provided.

When handling information with timestamps:
1. Each piece of information (both relationships and content) has a "created_at" timestamp indicating when we acquired this knowledge
2. When encountering conflicting information, consider both the content/relationship and the timestamp
3. Don't automatically prefer the most recent information - use judgment based on the context
4. For time-specific queries, prioritize temporal information in the content before considering creation timestamps

---Data Sources---

1. Knowledge Graph Data:
{kg_context}

2. Vector Data:
{vector_context}

---Response Requirements---

- Target format and length: {response_type}
- Use markdown formatting with appropriate section headings
- Aim to keep content around 3 paragraphs for conciseness
- Each paragraph should be under a relevant section heading
- Each section should focus on one main point or aspect of the answer
- Use clear and descriptive section titles that reflect the content
- List up to 5 most important reference sources at the end under "References", clearly indicating whether each source is from Knowledge Graph (KG) or Vector Data (VD)
  Format: [KG/VD] Source content
  
Add sections and commentary to the response as appropriate for the length and format. If the provided information is insufficient to answer the question, clearly state that you don't know or cannot provide an answer in the same language as the user's question."""
