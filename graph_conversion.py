# Quantum SPICE 
# Converts circuit information to capacitance & inductance graph

# arbitrary class for each components in the quantum circuit

class circComp(object):

    circCompList = []

    def __init__(self, name, type, terminals, value, connections, subsystem=None):
        # name (string) -> e.g. C1, I2
        self.name = name
        # type (string) => e.g. capacitor, inductor
        self.type = type
        # terminal (string tuple) => e.g. (C1_1, C1_2)
        self.terminals = terminals
        # value (string) => e.g. 4F, 15H
        self.value = value
        # connection (dictionary w string key and string list value) 
        # e.g. {C1_1: [C2_1, I1_2], C1_2: []}
        # stores list of connections between 
        # self.terminals (key) & other terminals (values)
        # no connection is shown by []
        self.connections = connections
        self.subsystem = subsystem
        # add circComp instance to circCompList
        circComp.circCompList.append(self)      

    def __del__(self):
        self.name = None
        self.type = None
        self.terminals = None
        self.value = None
        self.connections = None
        self.subsystem = None
        del self 

# clear circuit
def clearCircCompList():
    for comp in circComp.circCompList:
        circComp.__del__(comp)
    circComp.circCompList = []

#@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
##              Helper Functions              ##
#@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@

# return the circComp that has the input terminal
def getCompFromTerminal(terminal):
    for comp in circComp.circCompList:
        if terminal in comp.terminals:
            return comp
    raise Exception(terminal + " terminal doesn't exist, perhaps you have a wrong test case?")

# return other terminal in the same component 
# (assume only two terminals in a single componenet)
def getOtherTermSameComp(terminal):
    comp = getCompFromTerminal(terminal)
    for t in comp.terminals:
        if (t != terminal):
            return t
    
# return the value of the comp that 
# the terminal is in
def getValFromTerminal(terminal):
    comp = getCompFromTerminal(terminal)
    return comp.value

def getCompFromName(name):
    for comp in circComp.circCompList:
        if comp.name == name:
            return comp
    raise Exception(comp + " comp doesn't exist")  

# convert string val to int
def valToInt(val):
    num = ''  
    for c in val:
        if c.isdigit():
            num += c
    return int(num)

def getSet(term, cons):
    conSet = set()
    conSet.update(cons)
    conSet.add(term)
    # nodeDict's key is frozenset
    return frozenset(conSet)

# return node name if terminal is in nodeDict
# otherwise, return None
def tInDict(term, dict):
    for entry in dict:
        if term in entry:
            return dict[entry]
    return None

def nodeInList(node1, node2, nTups):
    if (node1, node2) in nTups or (node2, node1) in nTups:
        return True
    else: 
        return False

#@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
##              Main Functions              ##
#@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@

def convertParallel():
    # make 2d list of comps connected in parallel
    parallelConnections = []
    existingComp = []
    for comp in circComp.circCompList:
        if comp not in existingComp:
            conInParallel = [comp]
            connected1 = []
            for term in comp.connections:
                for con in comp.connections[term]:
                    conComp = getCompFromTerminal(con)
                    # if same type, add in the same list 
                    if conComp.type == comp.type:
                        # if same comp connected to both terminals
                        if conComp in connected1:
                            conInParallel.append(conComp)
                        else:
                            connected1.append(conComp)     
            if len(conInParallel) > 1:
                parallelConnections.append(conInParallel)
                for c in conInParallel:
                    existingComp.append(c)
    # loop through parallelConnections list,
    # replace parallel-conneted comps with single comp
    # don't remove junctions for now
    for con in parallelConnections:
        newVal = 0 
        # get new index so that name doesn't overlap
        ind = str(len(circComp.circCompList) + 1)
        if con[0].type == "capacitor":       
            # make new connections dictionary
            newConDict = {}
            newConDict["C" + ind + "_1"] = con[0].connections[con.terminals[0]]
            newConDict["C" + ind + "_2"] = con[0].connections[con.terminals[1]]
            for comp in con:
                # add capacitance in parallel
                newVal += valToInt(comp.value)
                # remove redundant connections
                for t in comp.terminals:
                    for conDictTerm in newConDict:
                        if t in newConDict[conDictTerm]:
                            newConDict[conDictTerm].remove(t) 
                circComp.circCompList.remove(comp)      
            totalVal = str(newVal) + "F"          
            # add new capacitor, remove old ones 
            circComp("C" + ind, "capacitor", ("C" + ind + "_1", "C" + ind + "_2"), 
                totalVal, newConDict) 
        elif con[0].type == "inductor":
             # make new connections dictionary
            newConDict = {}
            newConDict["C" + ind + "_1"] = con[0].connections[con.terminals[0]]
            newConDict["C" + ind + "_2"] = con[0].connections[con.terminals[1]]
            for comp in con:
                # inverse -- 
                newVal +=  1 / valToInt(comp.value)
                # remove redundant connections
                for t in comp.terminals:
                    for conDictTerm in newConDict:
                        if t in newConDict[conDictTerm]:
                            newConDict[conDictTerm].remove(t)  
                circComp.circCompList.remove(comp)
            # rounding?    
            totalVal = str(1 / newVal) + "H"          
            # add new capacitor, remove old ones 
            circComp("I" + ind, "inductor", ("I" + ind + "_1", "I" + ind + "_2"), 
                totalVal, newConDict) 

        elif con[0].type == "junction": 
            # check other parallel-connected comps to see if there' any capacitors or inductors
            # if all parallel-comps in the group are junctions, throw RUNTIME ERROR #
            raise Exception ("junctions connected in parallel") 


# loop through each component, 
# return the list of nodes and the values between them
def getNodes():
    #convertParallel()
    nodeTups = {}
    nodeDict = {}
    ind = 0
    for comp in circComp.circCompList:
         # for each terminal,
        nodeName = 'n' + str(ind)
        for t in comp.terminals:
            connections = comp.connections[t]
            fSet = getSet(t, connections)
            
            # check if node already exist
            if not (fSet in nodeDict):
                # add to nodeDict
                ind += 1
                nodeName = 'n' + str(ind)
                nodeDict[fSet] = nodeName
            
            # check if connected to other node
            otherT = getOtherTermSameComp(t)
            node = tInDict(otherT, nodeDict)
            if node != None  and node != nodeName and not nodeInList(node, nodeName, nodeTups):
                val = getValFromTerminal(t)
                nodeTups[(node, nodeName)] = (val, comp.name)
    return nodeTups

def getSubsytemDict():
    # dictionary of subsystems
    # values are set of comps in particular subsystem
    subDict = {}
    for comp in circComp.circCompList:
        subSys = comp.subsystem
        if subSys not in subDict:
            subDict[subSys] = {comp}
        else:
            subDict[subSys].add(comp)
    return subDict

def getCompNameSS():
    # dictionary of subsystems
    # values are set of comps' names in particular subsystem
    subDict = {}
    for comp in circComp.circCompList:
        subSys = comp.subsystem
        if subSys not in subDict:
            subDict[subSys] = {comp.name}
        else:
            subDict[subSys].add(comp.name)
    return subDict


def getIndList(nodeTups):
    ind_list = []
    # one dictionary per subsystem
    ind_dict = {}
    subSysDict = getSubsytemDict()
    for subSys in subSysDict:
        for tup in nodeTups:         
            val = nodeTups[tup][0]
            comp = getCompFromName(nodeTups[tup][1])
            compSS = comp.subsystem
            # if has value of inductance and is in current subSys
            if val[-1] == 'H' and subSys == compSS:
                intVal = valToInt(val)
                ind_dict[tup] = intVal
        if ind_dict != {}:
            ind_list.append(ind_dict)
        ind_dict = {}
    return ind_list







def test():
    #@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
    ##                Test Case 1                 ##
    #@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@

    #         (S1)       (S1)  
    #       -- C1 --  -- C2 -- 
    #       |                  |
    # (S2)  I2                 I1 (S1)
    #       |                  |
    #        -- C3 -- ---------
    #           (S2)

    C1 = circComp("C1", "capacitor", ("C1_1", "C1_2"), "5F", {"C1_1": ["I2_2"], "C1_2": ["C2_1"]}, 'S1')
    C2 = circComp("C2", "capacitor", ("C2_1", "C2_2"), "7F", {"C2_1": ["C1_2"], "C2_2": ["I1_1"]}, 'S1') 
    I1 = circComp("I1", "inductor", ("I1_1", "I1_2"), "3H", {"I1_1": ["C2_2"], "I1_2": ["C3_1"]}, 'S1') 
    C3 = circComp("C3", "capacitor", ("C3_1", "C3_2"), "9F", {"C3_1": ["I1_2"], "C3_2": ["I2_1"]}, 'S2') 
    I2 = circComp("I2", "inductor", ("I2_1", "I2_2"), "11H", {"I2_1": ["C3_2"], "I2_2": ["C1_1"]}, 'S2') 
     
    print("Test case 1: nodeTups::")
    nodeT = getNodes()
    print("Node Dictionary::")
    print(nodeT)
    print("Subsystem Dictionary::")
    print(getCompNameSS())
    print("Ind_List::")
    print(getIndList(nodeT))
    print("\n")
    clearCircCompList()

    #@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@
    ##                Test Case 2                 ##
    #@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@

    #         (S1)       (S1)  
    #        -- C1 -- -- C2 --_ 
    #       |        |         |
    # (S2)  I3       C3 (S1)   I1 (S1)
    #       |        |         |
    #        -- I2 -- -- C4 ---
    #           (S2)     (S2)

    C1 = circComp("C1", "capacitor", ("C1_1", "C1_2"), "5F", {"C1_1": ["I3_1"], "C1_2": ["C2_1", "C3_1"]}, 'S1')
    C2 = circComp("C2", "capacitor", ("C2_1", "C2_2"), "7F", {"C2_1": ["C1_2", "C3_1"], "C2_2": ["I1_1"]}, 'S1') 
    C3 = circComp("C3", "capacitor", ("C3_1", "C3_2"), "9F", {"C3_1": ["C1_2", "C2_1"], "C3_2": ["C4_1", "I2_2"]}, 'S1') 
    I1 = circComp("I1", "inductor", ("I1_1", "I1_2"), "3H", {"I1_1": ["C2_2"], "I1_2": ["C4_2"]}, 'S1') 
    C4 = circComp("C4", "capacitor", ("C4_1", "C4_2"), "11F", {"C4_1": ["C3_2", "I2_2"], "C4_2": ["I1_2"]}, 'S2') 
    I2 = circComp("I2", "inductor", ("I2_1", "I2_2"), "20H", {"I2_1": ["I3_2"], "I2_2": ["C3_2", "C4_1"]}, 'S2') 
    I3 = circComp("I3", "inductor", ("I3_1", "I3_2"), "25H", {"I3_1": ["C1_1"], "I3_2": ["I2_1"]}, 'S2') 
     
    print("Test case 2: nodeTups::")
    nodeT = getNodes()
    print("Node Dictionary::")
    print(nodeT)
    print("Subsystem Dictionary::")
    print(getCompNameSS())
    print("Ind_List::")
    print(getIndList(nodeT))
    print("\n")
    clearCircCompList()

test()
