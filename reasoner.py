import sys
import os
from py4j.java_gateway import JavaGateway
from tabulate import tabulate
from pyvis.network import Network

class OntologyReasoner:
    def __init__(self, ontology_file):
        # Initialize the connection to Java Gateway and load the ontology
        self.gateway = JavaGateway()
        self.owl_parser = self.gateway.getOWLParser()
        self.formatter = self.gateway.getSimpleDLFormatter()
        self.el_factory = self.gateway.getELFactory()

        print("Loading ontology from file...")
        self.ontology = self.owl_parser.parseFile(ontology_file)
        print("Ontology loaded successfully!")

        # Convert conjunctions to binary representation
        print("Converting conjunctions to binary format...")
        self.gateway.convertToBinaryConjunctions(self.ontology)

        # Initialize reasoning structures
        self.subsumption_graph = {}
        self.equivalence_classes = {}
        self.disjoint_classes = set()

        # Process axioms in the ontology
        self._parse_ontology_axioms()

    def _concept_to_string(self, concept):
        """Convert concept object to string."""
        return self.formatter.format(concept)

    def _parse_ontology_axioms(self):
        """Parse and process all axioms in the ontology."""
        for axiom in self.ontology.tbox().getAxioms():
            axiom_type = axiom.getClass().getSimpleName()

            if axiom_type == "GeneralConceptInclusion":
                self._process_subsumption_axiom(axiom)
            elif axiom_type == "EquivalentClasses":
                self._process_equivalence_axiom(axiom)
            elif axiom_type == "DisjointClassesAxiom":
                self._process_disjoint_axiom(axiom)

    def _process_subsumption_axiom(self, axiom):
        """Process subsumption axioms, handle conjunctions."""
        lhs = axiom.lhs()
        rhs = axiom.rhs()
        lhs_str = self._concept_to_string(lhs)
        rhs_str = self._concept_to_string(rhs)

        if lhs.getClass().getSimpleName() == "Conjunction":
            left_conjunct = self._concept_to_string(lhs.getConjunct1())
            right_conjunct = self._concept_to_string(lhs.getConjunct2())
            self._add_subsumption_relation(left_conjunct, rhs_str)
            self._add_subsumption_relation(right_conjunct, rhs_str)

        self._add_subsumption_relation(lhs_str, rhs_str)

    def _process_equivalence_axiom(self, axiom):
        """Process equivalence axioms and create equivalence classes."""
        equivalences = [self._concept_to_string(cls) for cls in axiom.getEquivalentClasses()]
        for i, eq_class in enumerate(equivalences):
            self.equivalence_classes[eq_class] = set(equivalences[:i] + equivalences[i+1:])

    def _process_disjoint_axiom(self, axiom):
        """Handle disjoint class axioms."""
        disjoint_set = [self._concept_to_string(cls) for cls in axiom.getDisjointClasses()]
        for i in range(len(disjoint_set)):
            for j in range(i + 1, len(disjoint_set)):
                self.disjoint_classes.add((disjoint_set[i], disjoint_set[j]))

    def _add_subsumption_relation(self, lhs, rhs):
        """Store subsumption relation in the graph."""
        if lhs not in self.subsumption_graph:
            self.subsumption_graph[lhs] = set()
        self.subsumption_graph[lhs].add(rhs)

    def compute_subsumers_and_subclasses(self, concept):
        """Compute the subsumption hierarchy and subclasses for a given concept."""
        subsumers = set()   # To store the superclasses (subsumers)
        subclasses = set()  # To store the direct subclasses
        reasoning_steps = []  # To track reasoning steps

        # 1. Find all subsumers (superclasses) for the given concept
        # We use a queue to perform a breadth-first search (BFS)
        queue = [concept]
        while queue:
            current = queue.pop(0)
            
            # Look for the direct superclasses (subsumers) of current class
            if current in self.subsumption_graph:
                for super_concept in self.subsumption_graph[current]:
                    if super_concept not in subsumers:
                        subsumers.add(super_concept)
                        reasoning_steps.append(f"Direct subsumption: {current} ⊑ {super_concept}")
                        queue.append(super_concept)  # Add the super-concept to the queue for further exploration

        # 2. Find **direct subclasses** for the given concept
        # Check for axioms that specify this concept as a subclass
        for axiom in self.ontology.tbox().getAxioms():
            axiom_type = axiom.getClass().getSimpleName()
            
            if axiom_type == "GeneralConceptInclusion":
                lhs = axiom.lhs()
                rhs = axiom.rhs()
                lhs_str = self._concept_to_string(lhs)
                rhs_str = self._concept_to_string(rhs)

                # Look for axioms where the concept is on the RHS of the inclusion, i.e., it is a subclass of the LHS.
                if rhs_str == concept:  # If the rhs is the concept, lhs is a direct superclass
                    subclasses.add(lhs_str)
                    reasoning_steps.append(f"Direct subclass: {lhs_str} ⊑ {concept}")

        return subsumers, subclasses, reasoning_steps



    def reason_about_concept(self, class_name):
        """Reason about a specific concept in the ontology."""
        if not (class_name.startswith('"') and class_name.endswith('"')):
            class_name = f'"{class_name}"'

        concept = self.el_factory.getConceptName(class_name)
        concept_str = self._concept_to_string(concept)

        subsumers, subclasses, reasoning_steps = self.compute_subsumers_and_subclasses(concept_str)

        # Display reasoning results
        print("\nDirect Subsumers (Superclasses):")
        if subsumers:
            print(tabulate([[s] for s in sorted(subsumers)], headers=["Superclasses"], tablefmt="pretty"))
        else:
            print("No direct superclasses found.")

        print("\nDirect Subclasses:")
        if subclasses:
            print(tabulate([[s] for s in sorted(subclasses)], headers=["Subclasses"], tablefmt="pretty"))
        else:
            print("No direct subclasses found.")

        print("\nReasoning Steps:")
        for step in reasoning_steps:
            print(f"  {step}")

        return subsumers, subclasses


    def visualize_ontology(self):
        """Visualize the ontology as an interactive graph."""
        network = Network(height="750px", width="100%", bgcolor="#222222", font_color="white", notebook=True)
        network.force_atlas_2based(gravity=-50)

        nodes = set()
        edges = set()

        for axiom in self.ontology.tbox().getAxioms():
            axiom_type = axiom.getClass().getSimpleName()
            if axiom_type == "GeneralConceptInclusion":
                lhs = self.formatter.format(axiom.lhs())
                rhs = self.formatter.format(axiom.rhs())
                for node, color in [(lhs, "#97c2fc"), (rhs, "#ffcccb")]:
                    if node not in nodes:
                        network.add_node(node, label=node, color=color)
                        nodes.add(node)
                
                edge = (lhs, rhs)
                if edge not in edges:
                    network.add_edge(lhs, rhs, title="Subsumes")
                    edges.add(edge)

        output_file = "ontology_visualization.html"
        network.show(output_file)
        print(f"Interactive ontology visualization saved as '{output_file}'")

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
    subsumers, subclasses = reasoner.reason_about_concept(class_name)
    reasoner.visualize_ontology()

if __name__ == "__main__":
    main()
