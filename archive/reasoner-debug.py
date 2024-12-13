import sys
import os
from py4j.java_gateway import JavaGateway

class OntologyReasoner:
    def __init__(self, ontology_file):
        """Initialize the reasoner and load the ontology."""
        self.gateway = JavaGateway()
        self.owl_parser = self.gateway.getOWLParser()
        self.formatter = self.gateway.getSimpleDLFormatter()
        self.el_factory = self.gateway.getELFactory()

        print("Loading ontology from file...")
        self.ontology = self.owl_parser.parseFile(ontology_file)
        print("Ontology loaded successfully!")

        print("Converting conjunctions to binary format...")
        self.gateway.convertToBinaryConjunctions(self.ontology)

        self.subsumption_graph = {}
        self._parse_ontology_axioms()

    def _concept_to_string(self, concept):
        """Convert concept object to a readable string."""
        return self.formatter.format(concept)

    def _parse_ontology_axioms(self):
        """Parse axioms from the ontology and populate reasoning structures."""
        print("\nParsing ontology axioms...")
        for axiom in self.ontology.tbox().getAxioms():
            axiom_type = axiom.getClass().getSimpleName()
            print(f"Processing axiom of type: {axiom_type}")
            
            if axiom_type == "GeneralConceptInclusion":
                self._process_subsumption_axiom(axiom)

        # Debugging output for the internal state
        print("\nSubsumption Graph:")
        for lhs, rhs_set in self.subsumption_graph.items():
            print(f"  {lhs} -> {rhs_set}")

    def _process_subsumption_axiom(self, axiom):
        """Process subsumption axioms and handle conjunctions."""
        lhs = axiom.lhs()
        rhs = axiom.rhs()
        lhs_str = self._concept_to_string(lhs)
        rhs_str = self._concept_to_string(rhs)

        if lhs.getClass().getSimpleName() == "Conjunction":
            for conjunct in [lhs.getConjunct1(), lhs.getConjunct2()]:
                conjunct_str = self._concept_to_string(conjunct)
                self._add_subsumption_relation(conjunct_str, rhs_str)
        else:
            self._add_subsumption_relation(lhs_str, rhs_str)

    def _add_subsumption_relation(self, lhs_str, rhs_str):
        """Helper to add subsumption relations to the graph."""
        if lhs_str not in self.subsumption_graph:
            self.subsumption_graph[lhs_str] = set()
        self.subsumption_graph[lhs_str].add(rhs_str)

    def get_subsumptions_for_class(self, class_name):
        """Return a set of all subsumptions for a specific class."""
        class_name = class_name.strip('"')  # Clean up the class name
        return self.subsumption_graph.get(class_name, set())

def main():
    if len(sys.argv) != 3:
        print("Usage: python ontology_reasoner.py ONTOLOGY_FILE CLASS_NAME")
        sys.exit(1)

    ontology_file = sys.argv[1]
    class_name = sys.argv[2]

    if not os.path.exists(ontology_file):
        print(f"Error: Ontology file '{ontology_file}' does not exist.")
        sys.exit(1)

    reasoner = OntologyReasoner(ontology_file)

    # Get the subsumptions for the given class
    subsumptions = reasoner.get_subsumptions_for_class(class_name)
    
    # Output subsumptions as a set
    print(f"Subsumptions for class '{class_name}': {subsumptions}")

if __name__ == "__main__":
    main()
