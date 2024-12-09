#! /usr/bin/python

from py4j.java_gateway import JavaGateway

# connect to the java gateway of dl4python
gateway = JavaGateway()

# get a parser from OWL files to DL ontologies
parser = gateway.getOWLParser()

# get a formatter to print in nice DL format
formatter = gateway.getSimpleDLFormatter()

print("Loading the ontology...")

# load an ontology from a file
ontology = parser.parseFile("dumplings.owl")

print("Loaded the ontology!")

# IMPORTANT: the algorithm from the lecture assumes conjunctions to always be over two concepts
# Ontologies in OWL can however have conjunctions over an arbitrary number of concpets.
# The following command changes all conjunctions so that they have at most two conjuncts
print("Converting to binary conjunctions")
gateway.convertToBinaryConjunctions(ontology)

# get the TBox axioms
tbox = ontology.tbox()
axioms = tbox.getAxioms()

print("These are the axioms in the TBox:")
for axiom in axioms:
    print(formatter.format(axiom))

# get all concepts occurring in the ontology
allConcepts = ontology.getSubConcepts()

print("There are ", len(allConcepts), " concepts occurring in the ontology")
print("These are the concepts occurring in the ontology:")
print([formatter.format(x) for x in allConcepts])

conceptNames = ontology.getConceptNames()

print("There are ", len(conceptNames), " concept names occurring in the ontology")
print("These are the concept names: ")
print([formatter.format(x) for x in conceptNames])

# access the type of axioms:
foundGCI = False
foundEquivalenceAxiom = False
print("Looking for axiom types in EL")
for axiom in axioms:
    axiomType = axiom.getClass().getSimpleName()
    if(not(foundGCI) and axiomType == "GeneralConceptInclusion"):
        print("I found a general concept inclusion:")
        print(formatter.format(axiom))
        print("The left hand side of the axiom is: ", formatter.format(axiom.lhs()))
        print("The right hand side of the axiom is: ", formatter.format(axiom.rhs()))
        print()
        foundGCI = True
    elif(not(foundEquivalenceAxiom) and axiomType == "EquivalenceAxiom"):
        print("I found an equivalence axiom:")
        print(formatter.format(axiom))
        print("The concepts made equivalent are: ")
        for concept in axiom.getConcepts():
            print(" - "+formatter.format(concept))
        foundEquivalenceAxiom = True

# accessing the relevant types of concepts:
foundConceptName=False
foundTop=False
foundExistential=False
foundConjunction=False
foundConceptTypes = set()

print("Looking for concept types in EL")
for concept in allConcepts:
    conceptType = concept.getClass().getSimpleName()
    if(not(conceptType in foundConceptTypes)): 
        print(conceptType)
        foundConceptTypes.add(conceptType)
    if(not(foundConceptName) and conceptType == "ConceptName"):
        print("I found a concept name: "+formatter.format(concept))
        print()
        foundConceptName = True
    elif(not(foundTop) and conceptType == "TopConcept$"):
        print("I found the top concept: "+formatter.format(concept))
        print()
        foundTop = True
    elif(not(foundExistential) and conceptType == "ExistentialRoleRestriction"):
        print("I found an existential role restriction: "+formatter.format(concept))
        print("The role is: "+formatter.format(concept.role()))
        print("The filler is: "+formatter.format(concept.filler()))
        print()
        foundExistential = True
    elif(not(foundConjunction) and conceptType == "ConceptConjunction"):
        print("I found a conjunction: "+formatter.format(concept))
        print("The conjuncts are: ")
        for conjunct in concept.getConjuncts():
            print(" - "+formatter.format(conjunct))
        print()
        foundConjunction=True

# Creating EL concepts and axioms

elFactory = gateway.getELFactory()

conceptA = elFactory.getConceptName("A")
conceptB = elFactory.getConceptName("B")
conjunctionAB = elFactory.getConjunction(conceptA, conceptB)
role = elFactory.getRole("r")
existential = elFactory.getExistentialRoleRestriction(role, conjunctionAB)
top = elFactory.getTop()
conjunction2 = elFactory.getConjunction(top, existential)

gci = elFactory.getGCI(conjunctionAB, conjunction2)

print("I made the following GCI:")
print(formatter.format(gci))

# Using the reasoners

elk = gateway.getELKReasoner()
hermit = gateway.getHermiTReasoner() # might the upper case T!

dumpling_concept = elFactory.getConceptName("dumplings:Dumpling")

def print_results(reasoner, concept):
    print(f"\nResults from {reasoner.__class__.__name__}:")
    reasoner.setOntology(ontology)

    # Get the subsumers for the given concept
    subsumers = reasoner.getSubsumers(concept)
    print(f"According to {reasoner.__class__.__name__}, {formatter.format(concept)} has the following subsumers:")
    for subsumer in subsumers:
        print(" - ", formatter.format(subsumer))
    print(f"({len(subsumers)} in total)")

    # Classify the ontology and print the result
    classificationResult = reasoner.classify()
    print("Classification result: (too large to display)")

# Option to print classification and subsumer results
should_print = True  # Set to False to skip printing

if should_print:
    print_results(elk, dumpling_concept)
    print_results(hermit, dumpling_concept)
else:
    print("Results will not be printed.")
