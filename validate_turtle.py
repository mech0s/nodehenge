import argparse
from rdflib import Graph, URIRef, Literal
from rdflib.namespace import SKOS, RDF

def validate_turtle_file(filepath):
    """
    Validates a Turtle file, including SKOS integrity checks.
    """
    graph = Graph()
    try:
        graph.parse(filepath, format='turtle')
        print(f"Successfully parsed {filepath}")

        # SKOS Integrity Checks
        check_concept_scheme_typing(graph, filepath)
        check_ordered_collection_members(graph, filepath)

    except Exception as e:
        print(f"Error parsing {filepath}: {e}")

def check_concept_scheme_typing(graph, filepath):
    """
    Checks if concepts in a skos:ConceptScheme are typed as skos:Concept.
    """
    # Find all concepts that are part of any concept scheme
    for concept, scheme in graph.subject_objects(SKOS.inScheme):
        # Check if the scheme is actually a skos:ConceptScheme
        if (scheme, RDF.type, SKOS.ConceptScheme) in graph:
            if not (concept, RDF.type, SKOS.Concept) in graph:
                print(f"Warning in {filepath}: Concept {concept} linked to scheme {scheme} via skos:inScheme is not explicitly typed as skos:Concept.")

    # Also check concepts linked via skos:hasTopConcept / skos:topConceptOf
    for scheme, concept in graph.subject_objects(SKOS.hasTopConcept):
        if (scheme, RDF.type, SKOS.ConceptScheme) in graph: # Ensure the scheme is a ConceptScheme
            if not (concept, RDF.type, SKOS.Concept) in graph:
                print(f"Warning in {filepath}: Concept {concept} linked to scheme {scheme} via skos:hasTopConcept is not explicitly typed as skos:Concept.")
    
    # skos:topConceptOf is inverse of skos:hasTopConcept
    for concept, scheme in graph.subject_objects(SKOS.topConceptOf):
         if (scheme, RDF.type, SKOS.ConceptScheme) in graph: # Ensure the scheme is a ConceptScheme
            if not (concept, RDF.type, SKOS.Concept) in graph:
                print(f"Warning in {filepath}: Concept {concept} linked to scheme {scheme} via skos:topConceptOf is not explicitly typed as skos:Concept.")


def check_ordered_collection_members(graph, filepath):
    """
    Checks members of a skos:OrderedCollection.
    """
    for collection in graph.subjects(RDF.type, SKOS.OrderedCollection):
        # skos:memberList points to an rdf:List
        for rdf_list_head in graph.objects(collection, SKOS.memberList):
            current_node = rdf_list_head
            processed_members = set() # To handle potential cycles in rdf:List, though unlikely in SKOS
            
            while current_node and current_node != RDF.nil and current_node not in processed_members:
                processed_members.add(current_node)
                member = graph.value(subject=current_node, predicate=RDF.first)
                
                if member:
                    if isinstance(member, Literal):
                        print(f"Warning in {filepath}: Member '{member}' in collection {collection} is a literal, not a resource.")
                    # Check if the member exists as a subject of any triple in the graph.
                    # (member, None, None) checks if 'member' is a subject.
                    # (None, None, member) checks if 'member' is an object.
                    # For a resource to "exist" in the graph, it should ideally be a subject of some statement,
                    # or at least defined (e.g. ex:myMember a skos:Concept).
                    # A simple check is to see if it appears as a subject.
                    elif not list(graph.triples((member, None, None))):
                        print(f"Warning in {filepath}: Member {member} in collection {collection} does not appear as a subject of any statement in the graph (i.e., it may not be defined).")
                else:
                    # This case (rdf:first is missing) would be an invalid RDF list structure.
                    print(f"Warning in {filepath}: Collection {collection} has an invalid list structure starting at {current_node}: rdf:first is missing.")

                current_node = graph.value(subject=current_node, predicate=RDF.rest)
            
            if current_node in processed_members and current_node != RDF.nil:
                 print(f"Warning in {filepath}: RDF list for collection {collection} contains a cycle at {current_node}.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate Turtle files with SKOS integrity checks.")
    parser.add_argument("files", nargs="+", help="List of Turtle files to validate.")
    args = parser.parse_args()

    for filepath in args.files:
        validate_turtle_file(filepath)
