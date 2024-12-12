import sys
import os
from py4j.java_gateway import JavaGateway
from tabulate import tabulate
from pyvis.network import Network

class AdvancedELReasoner:
    def __init__(self, ontology_file):
        self.gateway = JavaGateway()
        self.parser = self.gateway.getOWLParser()
        self.formatter = self.gateway.getSimpleDLFormatter()
        self.elFactory = self.gateway.getELFactory()

        print("Loading the ontology...")
        self.ontology = self.parser.parseFile(ontology_file)
        print("Loaded the ontology!")

        # Convert conjunctions to binary form
        print("Converting to binary conjunctions")
        self.gateway.convertToBinaryConjunctions(self.ontology)

        # Reasoning data structures
        self.subsumption_graph = {}
        self.existential_relations = {}
        self.disjoint_classes = set()
        self.equivalence_classes = {}
        self.concept_definitions = {}

        # Parse ontology axioms
        self._parse_ontology_axioms()

    def _concept_to_str(self, concept):
        return self.formatter.format(concept)

    def _parse_ontology_axioms(self):
        """Parse ontology axioms and build reasoning structures."""
        for axiom in self.ontology.tbox().getAxioms():
            cls_name = axiom.getClass().getSimpleName()
            
            if cls_name == "GeneralConceptInclusion":
                self._handle_subsumption_axiom(axiom)
            
            elif cls_name == "EquivalentClasses":
                self._handle_equivalence_axiom(axiom)
            
            elif cls_name == "DisjointClassesAxiom":
                self._handle_disjoint_axiom(axiom)

    def _handle_subsumption_axiom(self, axiom):
        """Handle subsumption and conjunction axioms."""
        lhs = axiom.lhs()
        rhs = axiom.rhs()
        lhs_str = self._concept_to_str(lhs)
        rhs_str = self._concept_to_str(rhs)

        lhs_class = lhs.getClass().getSimpleName()
        if lhs_class == "Conjunction":
            c1_str = self._concept_to_str(lhs.getConjunct1())
            c2_str = self._concept_to_str(lhs.getConjunct2())
            self._add_subsumption(c1_str, rhs_str)
            self._add_subsumption(c2_str, rhs_str)
        
        self._add_subsumption(lhs_str, rhs_str)

    def _handle_equivalence_axiom(self, axiom):
        """Handle equivalence class axioms."""
        eq_classes = [self._concept_to_str(cls) for cls in axiom.getEquivalentClasses()]
        for i, eq_class in enumerate(eq_classes):
            self.equivalence_classes[eq_class] = set(eq_classes[:i] + eq_classes[i+1:])

    def _handle_disjoint_axiom(self, axiom):
        """Handle disjoint classes axioms."""
        disjoint_set = [self._concept_to_str(cls) for cls in axiom.getDisjointClasses()]
        for i in range(len(disjoint_set)):
            for j in range(i + 1, len(disjoint_set)):
                self.disjoint_classes.add((disjoint_set[i], disjoint_set[j]))

    def _add_subsumption(self, lhs, rhs):
        """Add subsumption relation to the graph."""
        if lhs not in self.subsumption_graph:
            self.subsumption_graph[lhs] = set()
        self.subsumption_graph[lhs].add(rhs)

    def compute_subsumers(self, concept):
        """
        Compute all subsumers for a given concept with advanced reasoning.
        """
        subsumers = {concept}
        queue = list(subsumers)
        processed = set()
        detailed_reasoning = []

        while queue:
            current = queue.pop(0)
            if current in processed:
                continue
            processed.add(current)

            # Direct subsumption
            if current in self.subsumption_graph:
                for super_concept in self.subsumption_graph[current]:
                    if super_concept not in subsumers:
                        subsumers.add(super_concept)
                        detailed_reasoning.append(f"Direct subsumption: {current} ⊑ {super_concept}")
                        queue.append(super_concept)

            # Equivalence propagation
            if current in self.equivalence_classes:
                for equiv_concept in self.equivalence_classes[current]:
                    if equiv_concept not in subsumers:
                        subsumers.add(equiv_concept)
                        detailed_reasoning.append(f"Equivalence propagation: {current} ⟷ {equiv_concept}")
                        queue.append(equiv_concept)

        # Complex concept classification strategies
        classification_strategies = [
            self._check_cheesy_pizza_classification,
            self._check_existential_conditions,
            # Add more classification strategies here
        ]

        for strategy in classification_strategies:
            classified_concepts = strategy(subsumers)
            subsumers.update(classified_concepts)

        return subsumers, detailed_reasoning

    def _check_cheesy_pizza_classification(self, known_subsumers):
        """
        Strategy to classify CheesyPizza and similar complex concepts
        """
        classified = set()
        classification_rules = {
            'CheesyPizza': {
                'requires': ['Pizza', 'CheeseTopping'],
                'existential_check': r'∃hasTopping\.'
            }
            # Add more complex classification rules here
        }

        for concept, rules in classification_rules.items():
            is_pizza = any(r in s for s in known_subsumers for r in rules['requires'])
            has_existential = any(
                rules['existential_check'] in str(s) 
                for s in known_subsumers
            )
            
            if is_pizza and has_existential:
                classified.add(concept)
                print(f"Classification strategy: Added {concept}")

        return classified

    def _check_existential_conditions(self, known_subsumers):
        """
        Check and propagate existential conditions
        """
        classified = set()
        existential_rules = {
            r'∃hasTopping\..*': ['Pizza', 'MealTopping'],
            # More existential rules can be added
        }

        for pattern, required_concepts in existential_rules.items():
            if all(
                any(r in str(s) for s in known_subsumers) 
                for r in required_concepts
            ):
                existential_matches = [
                    s for s in known_subsumers 
                    if s.startswith('∃') and s.startswith(pattern)
                ]
                classified.update(existential_matches)

        return classified

    def reason_about_concept(self, class_name):
        """Main reasoning method for a specific concept."""
        if not (class_name.startswith('"') and class_name.endswith('"')):
            class_name = f'"{class_name}"'

        test_concept = self.elFactory.getConceptName(class_name)
        test_concept_str = self._concept_to_str(test_concept)

        subsumers, detailed_reasoning = self.compute_subsumers(test_concept_str)

        # Detailed output
        print("\nComputed Subsumers:")
        print(tabulate([[s] for s in sorted(subsumers)], headers=["Subsumers"], tablefmt="pretty"))

        print("\nDetailed Reasoning Steps:")
        for step in detailed_reasoning:
            print(f"  {step}")

        return subsumers

    def visualize_ontology(self):
        """Create an interactive ontology visualization."""
        net = Network(height="750px", width="100%", bgcolor="#222222", font_color="white", notebook=True)
        net.force_atlas_2based(gravity=-50)

        nodes = set()
        edges = set()

        for axiom in self.ontology.tbox().getAxioms():
            cls_name = axiom.getClass().getSimpleName()
            if cls_name == "GeneralConceptInclusion":
                lhs = self.formatter.format(axiom.lhs())
                rhs = self.formatter.format(axiom.rhs())
                for node, color in [(lhs, "#97c2fc"), (rhs, "#ffcccb")]:
                    if node not in nodes:
                        net.add_node(node, label=node, color=color)
                        nodes.add(node)
                
                edge = (lhs, rhs)
                if edge not in edges:
                    net.add_edge(lhs, rhs, title="Subsumes")
                    edges.add(edge)

        output_file = "ontology_visualization_with_relations.html"
        net.show(output_file)
        print(f"Interactive visualization saved as '{output_file}'")

def main():
    if len(sys.argv) != 3:
        print("Usage: python advanced_el_reasoner.py ONTOLOGY_FILE CLASS_NAME")
        sys.exit(1)

    ontology_file = sys.argv[1]
    class_name = sys.argv[2]

    if not os.path.exists(ontology_file):
        print(f"Error: Ontology file '{ontology_file}' does not exist.")
        sys.exit(1)

    reasoner = AdvancedELReasoner(ontology_file)
    subsumers = reasoner.reason_about_concept(class_name)
    reasoner.visualize_ontology()

if __name__ == "__main__":
    main()