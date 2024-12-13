from py4j.java_gateway import JavaGateway
import sys
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')

gateway = JavaGateway()

# 😎
class ELReasoner5000: 
    def __init__(self):
        # JAVA STUFF
        self.elFactory = gateway.getELFactory()
        self.formatter = gateway.getSimpleDLFormatter()
        self.parser = gateway.getOWLParser()

    def get_the_box(self, ontology):
        '''GET THE Tbox FROM THE ONTOLOGY'''
        gateway.convertToBinaryConjunctions(ontology)
        return ontology.tbox()
    
    def get_axiom_type(self, axiom): 
        '''FIND OUT WHAT KIND OF AXIOM IT IS'''
        return axiom.getClass().getSimpleName()

    def convert_tbox_to_subsumers(self, tbox):
        ''' ABOUT SUBSUMERS? '''
        new_tbox = []
        axioms = tbox.getAxioms()

        for axiom in axioms: 
            axiom_type = self.get_axiom_type(axiom)
            if axiom_type == 'EquivalenceAxiom': 
                concepts = axiom.getConcepts()
                A = concepts[0]
                B = concepts[1]
                gci1 = self.elFactory.getGCI(A, B)
                gci2 = self.elFactory.getGCI(B, A)
                new_tbox.append(gci1)
                new_tbox.append(gci2)
            else: 
                new_tbox.append(axiom)

        top = self.elFactory.getTop()
        new_tbox.append(top)
        return new_tbox

    def get_concepts_in_ontology(self, ontology):
        '''GIMMIE ALL CONCEPTS IN  ONTOLOGY'''
        return ontology.getConceptNames()
    
    def check_if_subsumed(self, C0, concept_names, tbox):
        '''IS C0 BEING SUBSUMED BY ANOTHER CONCEPT D0?'''
        model = {'d0': {C0}} 
        relations = {'d0': dict()} 
   
        changed = True
        while changed:
            changed = False
            new_copy = list(model.items())
            for node, assigned in new_copy:
                
                # RULES, RULES, RULES! APPLY THEM ALL!
                for axiom in tbox:
                    axiom_type = self.get_axiom_type(axiom)
                    if axiom_type == "GeneralConceptInclusion":
                        if axiom.lhs() in assigned and axiom.rhs() not in assigned:
                            assigned.add(axiom.rhs())
                            changed = True
                
                top = self.elFactory.getTop()
                if top not in assigned:
                    assigned.add(top)
                    changed = True

                for concept in concept_names:
                    concept_type = self.get_axiom_type(concept)
                    
                    if concept_type == "ConceptConjunction":
                        conjuncts = concept.getConjuncts()
                        A = conjuncts[0]
                        B =  conjuncts[1]
                        if A in assigned and B in assigned and concept not in assigned:
                            assigned.add(concept)
                            changed = True

                # EXCITING STUFF: EXISTENTIAL RULES!
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

                        # APPLY AND RULE 1!
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
                        
                        for element, assignments in new_copy:  
                            if filler in assignments:
                                element_found = True
                                if node not in relations:
                                    relations[node] = {}

                                if role not in relations[node]:
                                    relations[node][role] = set()

                                if element not in relations[node][role]:
                                    relations[node][role].add(element)
                                    changed = True
                                      
                        if not element_found:
                            new_index = len(model)
                            new_node = f'd{new_index}'

                            if node not in relations:
                                relations[node] = {}

                            if role not in relations[node]:
                                relations[node][role] = set()

                            relations[node][role].add(new_node)
                            model[new_node] = {filler}  
                            changed = True  
  
                if changed:
                    break
    
        return model, relations     

    def find_all_subsumers(self, input_class, ontology):
        '''FIND ALL THE SUBSUMERS OF A SPECIFIC CLASS'''
        tbox = self.get_the_box(ontology)
        tbox = self.convert_tbox_to_subsumers(tbox)

        subsumers = []
        concept_names = ontology.getConceptNames()
        top = self.formatter.format(self.elFactory.getTop())
        
        first_concept = self.formatter.format(concept_names.iterator().next())
        if ("\"" in first_concept) & ("\"" not in input_class):
            C0 = self.elFactory.getConceptName('"' + input_class + '"')
        else:
            C0 = self.elFactory.getConceptName(input_class)

        if C0 in concept_names: 
            model, relations = self.check_if_subsumed(C0, concept_names, tbox)
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


    def show_subsumers_graph(self, input_class, subsumers):
        '''VISUALIZATIONSE'''
        if not subsumers:
            print(f"No subsumers found for {input_class}.")
            return

        G = nx.DiGraph()
        G.add_node(input_class, color="red", size=3000)

        for subsumer in subsumers:
            G.add_node(subsumer, color="#ADD8E6", size=2000)
            G.add_edge(subsumer, input_class)

        pos = nx.spring_layout(G)
        node_colors = [G.nodes[node]['color'] for node in G.nodes]
        node_sizes = [G.nodes[node]['size'] for node in G.nodes]

        plt.figure(figsize=(10, 8))
        nx.draw(G, pos, with_labels=True, node_color=node_colors, node_size=node_sizes, edge_color="black")
        plt.title(f"Subsumers of {input_class}")
        plt.savefig(f"{input_class}_subsumers.png")

# Running it..
if __name__ == '__main__':
    ontology_file = str(sys.argv[1])
    C0 = str(sys.argv[2])

    reasoner = ELReasoner5000()
    
    ontology = reasoner.parser.parseFile(ontology_file)
    gateway.convertToBinaryConjunctions(ontology)
    concept_names = ontology.getConceptNames()

    tbox = reasoner.get_the_box(ontology)
    subsumers = reasoner.find_all_subsumers(C0, ontology)
    if subsumers != None:
        for subsumer in subsumers:
            print(subsumer)

        reasoner.show_subsumers_graph(C0, subsumers)
