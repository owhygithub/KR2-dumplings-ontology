#! /usr/bin/python3

import sys
from py4j.java_gateway import JavaGateway

def main():
    if len(sys.argv) != 3:
        print("Usage: python reasoner.py DumplingOntology.owx Dumpling")
        sys.exit(1)

    ontology_file = sys.argv[1]
    class_name = sys.argv[2]

    # Connect to the Java gateway of dl4python
    gateway = JavaGateway()

    # Get the parser and formatter from dl4python
    parser = gateway.getOWLParser()
    formatter = gateway.getSimpleDLFormatter()

    try:
        # Load the ontology
        ontology = parser.parseFile(ontology_file)

        # Convert to binary conjunctions as required
        gateway.convertToBinaryConjunctions(ontology)

        # Initialize the EL reasoner
        elk = gateway.getELKReasoner()
        elk.setOntology(ontology)

        # Get the EL factory to work with concepts
        el_factory = gateway.getELFactory()
        target_concept = el_factory.getConceptName(class_name)

        # Compute subsumers for the given class
        subsumers = elk.getSubsumers(target_concept)

        # Print the subsumers, one per line
        for concept in sorted(subsumers, key=lambda x: formatter.format(x)):
            print(formatter.format(concept))

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
