from py4j.java_gateway import JavaGateway
import sys

# connect to the java gateway of dl4python
gateway = JavaGateway()

class ELreasoner: 
    def __init__(self):
        self.elFactory = gateway.getELFactory()
        self.formatter = gateway.getSimpleDLFormatter()
        self.parser = gateway.getOWLParser()


    def get_tbox(self, ontology):
        '''Returns the Tbox of a given ontology'''
        gateway.convertToBinaryConjunctions(ontology)
        return ontology.tbox()
    
    def get_axiom_type(self, axiom): 
        '''Returns the type of the axiom or concept given'''
        return axiom.getClass().getSimpleName()

    def convert_tbox(self, tbox):
        '''Converts all equivalence relations in the Tbox to subsumer relations
        
        Parameters: tbox: the Tbox to be converted
        
        Returns: a list of all axioms in the Tbox'''

        new_tbox = []
        axioms = tbox.getAxioms()

        # Loop over all axioms in the Tbox
        for axiom in axioms: 
            axiomType = self.get_axiom_type(axiom)
            # If the axiom is an equivalence axiom, replace by CGIs
            if axiomType == 'EquivalenceAxiom': 
                concepts = axiom.getConcepts()
                A = concepts[0]
                B = concepts[1]
                gci1 = self.elFactory.getGCI(A, B)
                gci2 = self.elFactory.getGCI(B, A)
                new_tbox.append(gci1)
                new_tbox.append(gci2)
            else: 
                new_tbox.append(axiom)
        # Add T to Tbox
        top = self.elFactory.getTop()
        new_tbox.append(top)
        return new_tbox

    def get_concept_names(self, ontology):
        '''Returns all concept names in a given ontology'''
        return ontology.getConceptNames()
    
    def check_subsumed(self, C0, concept_names, tbox):
        '''Checks for a single concept C0 whether it is subsumed by a concept D0
        
        Parameters: C0 and D0: the concepts that need to be checked
        O is entailed: C0 <= DO
        
        Returns: True or False: True when C0 is subsumed by D0, False if not'''
        
        model = {'d0': {C0}} 
        relations = {'d0': dict()} 
   
        changed = True
        while changed:
            changed = False
            new_copy = list(model.items())
            for node, assigned in new_copy:
                
                # GCI-rule: If d has C assigned and D is subsumed by C, assign D to d
                for axiom in tbox:
                    axiom_type = self.get_axiom_type(axiom)
                    if axiom_type == "GeneralConceptInclusion":
                        if axiom.lhs() in assigned and axiom.rhs() not in assigned:
                            assigned.add(axiom.rhs())
                            changed = True
                
                #⊤-rule: Add ⊤ to any individual
                top = self.elFactory.getTop()
                if top not in assigned:
                    assigned.add(top)
                    changed = True


                # And-rule 2: If d has C, D assigned, assign C and D to d.
                for concept in concept_names:
                    concept_type = self.get_axiom_type(concept)
                    
                    if concept_type == "ConceptConjunction":
                        conjuncts = concept.getConjuncts()
                        A = conjuncts[0]
                        B =  conjuncts[1]
                        if A in assigned and B in assigned and concept not in assigned:
                            assigned.add(concept)
                            changed = True

                # Existential-rule 2: If d has an r-successor with C assigned, add Existentialr.C to d
                if node in relations:
                    for role, successors in list(relations[node].items()):
                        for successor in list(successors):
                            for elem in set(model[successor]):
                                if elem !=  self.elFactory.getTop() and self.get_axiom_type(elem)=="ConceptName":
                                    rolerestriction = self.elFactory.getExistentialRoleRestriction(role, elem)
                                    if rolerestriction not in model[node]:
                                        model[node].add(rolerestriction)
                                        changed = True
            
                for concept in set(assigned):
                    concept_type = self.get_axiom_type(concept)
                    
                    if concept_type == "ConceptConjunction":
                        conjuncts= concept.getConjuncts()
                        A = conjuncts[0]
                        B =  conjuncts[1]

                        # And-rule 1: If d has C and D assigned, assign C, D to d.
                        if A not in assigned:
                            assigned.add(A)
                            changed = True
                            
                        if B not in assigned:
                            assigned.add(B)
                            changed = True

                    if concept_type == "ExistentialRoleRestriction":
                        role = concept.role()
                        filler = concept.filler()
                        element_found = False
                        # Existential-rule 1.1 
                        # If d has Existencer.C assigned and there is an element e with initial concept C assigned, make e the r-successor of d
                        for element, assignments in new_copy:  
                            if filler in assignments:
                                element_found = True
                                # If the node does not exist in relations dictionary yet, create it in the dictionary
                                if node not in relations:
                                    relations[node] = {}

                                # If the relation does not exist yet, add it to the dictionary of the node in relations
                                if role not in relations[node]:
                                    relations[node][role] = set()

                                # If the relation and node exist, but the successor is not assigned to the node yet, add it to the relation
                                if element not in relations[node][role]:
                                    relations[node][role].add(element)
                                    changed = True
                   

                        # Existential-rule 1.2 
                        # If d has Existencer.C assigned and there is no element e with initial concept C assigned, add a new r-successor to d, and assign to it as initial concept C.
                        if not element_found:
                            new_index = len(model)
                            new_node = f'd{new_index}'

                            # If the node is not yet in the relations dicitonary, create it
                            if node not in relations:
                                relations[node] = {}

                            # If the role is not in the relations of the node, create it and assign it to an empty set
                            if role not in relations[node]:
                                relations[node][role] = set()

                            # Now add the new relation to the relations of that node, and add the new node to the model
                            relations[node][role].add(new_node)
                            model[new_node] = {filler}  
                            changed = True  
  
                if changed:
                    break
    
        return model, relations     

    def get_subsumers(self, input_class, ontology):
        '''Returns all subsumers of a given class name
        
        Parameters: C0: The class name we want to know the subsumers of
        tbox: the Tbox corresponding to the ontology
        ontology: the ontology that we are examining

        Returns: a list of all subsumers of the given class name
        '''

        # Convert the axioms in the Tbox so it is appropriate for our reasoner
        tbox = self.get_tbox(ontology)
        tbox = self.convert_tbox(tbox)

        # Loop over all concept names to find the subsumers of the given class name
        subsumers = []
        concept_names = ontology.getConceptNames()
        print()
        top = self.formatter.format(self.elFactory.getTop())
        
        first_concept = self.formatter.format(concept_names.iterator().next())
        if ("\"" in first_concept) & ("\"" not in input_class):
            C0 = self.elFactory.getConceptName('"' + input_class + '"')
        else:
            C0 = self.elFactory.getConceptName(input_class)

        if C0 in concept_names: 
            model, relations = self.check_subsumed(C0, concept_names, tbox)
            found_top = False
            for D0 in concept_names: 
                
                if D0 in model['d0']:
                    subsumers.append(self.formatter.format(D0))
                elif not found_top:
                    D0 = self.elFactory.getTop()
                    if D0 in model['d0']:
                        subsumers.append(self.formatter.format(D0))
                        found_top = True
            subsumers = [subsum for subsum in subsumers if subsum != self.formatter.format(self.elFactory.getTop())]

            return subsumers

if __name__ == '__main__':
    ontology_file = str(sys.argv[1])

    C0 = str(sys.argv[2])

    reasoner = ELreasoner()
    
    ontology = reasoner.parser.parseFile(ontology_file)
    gateway.convertToBinaryConjunctions(ontology)
    concept_names = ontology.getConceptNames()

    tbox = reasoner.get_tbox(ontology)
    subsumers = reasoner.get_subsumers(C0, ontology)
    if subsumers != None:
        for subsumer in subsumers:
            print(subsumer)

