import sys
import os
from py4j.java_gateway import JavaGateway
from collections import deque

class OntologyReasoner:
    def __init__(self, ontology_file):
        # Initialize the connection to Java Gateway and load the ontology
        self.gateway = JavaGateway()
        self.owl_parser = self.gateway.getOWLParser()
        self.formatter = self.gateway.getSimpleDLFormatter()

        print("Loading ontology from file...")
        self.ontology = self.owl_parser.parseFile(ontology_file)
        print("Ontology loaded successfully!")

        # Initialize reasoning structures
        self.equivalence_classes = {}
        self.disjoint_classes = set()

        # Process axioms in the ontology
        self._parse_ontology_axioms()

    def _concept_to_string(self, concept):
        """Convert concept object to string."""
        return self.formatter.format(concept)

    def _parse_ontology_axioms(self):
        """Parse and process all axioms in the ontology."""
        if not self.ontology or not hasattr(self.ontology, 'tbox'):
            raise ValueError("Ontology or TBox is not available.")
        
        self.subsumption_axioms = []  # Store subsumption axioms
        for axiom in self.ontology.tbox().getAxioms():
            try:
                axiom_type = axiom.getClass().getSimpleName()
            except AttributeError:
                axiom_type = None

            if axiom_type == "GeneralConceptInclusion":
                self._process_subsumption_axiom(axiom)
            elif axiom_type == "EquivalentClasses":
                self._process_equivalence_axiom(axiom)
            elif axiom_type == "DisjointClassesAxiom":
                self._process_disjoint_axiom(axiom)
            else:
                print(f"Unknown axiom type: {axiom_type}")

    def _process_subsumption_axiom(self, axiom):
        """Process subsumption axioms."""
        lhs = axiom.lhs()
        rhs = axiom.rhs()

        if lhs is None or rhs is None:
            raise ValueError("LHS or RHS of subsumption axiom is None.")

        lhs_str = self._concept_to_string(lhs)
        rhs_str = self._concept_to_string(rhs)

        # Store subsumption axioms
        self.subsumption_axioms.append((lhs_str, rhs_str))

    def _process_equivalence_axiom(self, axiom):
        """Process equivalence axioms."""
        equivalences = [self._concept_to_string(cls) for cls in axiom.getEquivalentClasses()]
        if not equivalences:
            raise ValueError("No equivalence classes found in the axiom.")

        for eq_class in equivalences:
            self.equivalence_classes[eq_class] = set(equivalences) - {eq_class}

    def _process_disjoint_axiom(self, axiom):
        """Process disjoint classes."""
        disjoint_set = [self._concept_to_string(cls) for cls in axiom.getDisjointClasses()]
        if not disjoint_set:
            raise ValueError("No disjoint classes found in the axiom.")

        for i in range(len(disjoint_set)):
            for j in range(i + 1, len(disjoint_set)):
                self.disjoint_classes.add((disjoint_set[i], disjoint_set[j]))

    def compute_subsumers(self, concept):
        """Compute the subsumption hierarchy for a given concept."""
        subsumers = set()
        
        # Look for subsumers directly from subsumption axioms
        for lhs, rhs in self.subsumption_axioms:
            if rhs == concept:
                subsumers.add(lhs)
        
        return subsumers

    def reason_about_concept(self, class_name):
        """Reason about a specific concept."""
        subsumers = self.compute_subsumers(class_name)
        subsumers.add(class_name)  # Add the class itself as a subsumer
        return subsumers


def main():
    if len(sys.argv) != 3:
        print("Usage: python reasoner.py ONTOLOGY_FILE CLASS_NAME")
        sys.exit(1)

    ontology_file = sys.argv[1]
    class_name = sys.argv[2]

    if not os.path.exists(ontology_file):
        print(f"Error: Ontology file '{ontology_file}' does not exist.")
        sys.exit(1)

    reasoner = OntologyReasoner(ontology_file)

    # Compute the subsumers
    subsumers = reasoner.reason_about_concept(class_name)

    print("\nSubsumers:")
    print(subsumers)  # Only print the subsumers without additional messages


if __name__ == "__main__":
    main()
