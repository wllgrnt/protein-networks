from bson.objectid import ObjectId
import proteinnetworks.partition
import proteinnetworks.insight
import pytest
import numpy as np
import networkx as nx
import math
"""
Unit tests for the Insight module.

Units

SuperNetwork
    __init__
    fromPartitionId (classmethod, weird)
    draw
    getIsomorphs
    getWeakIsomorphs

SuperNetworkNullModel

getModifiedJaccard
getZScore
generateNullModel
getMCS
getShannonEntropy
getMutualInfo
getNMI
getConductanceFromPartition
getConductanceFromNodeSubset
getModularityFromPartition
getModularityFromAdjacencyMatrix
edgelistToGraph
"""


"""
Tests for SuperNetwork.__init__()
Inputs: inputPartition, level (int, defaults to None)

Outputs: a SuperNetwork

Options: Multi-chain input partition legit
         Single-chain input partiton legit
         Partition doesn't have given level
         Arguments are invalid

"""


def test_supernetwork_init_all_options_valid_no_level(mock_database):
    """
    Checks that valid inputs gives the correct output.

    If the partition is a valid Partition, and no level is given then a Supernetwork is generated.
    I.e. no supernetwork is in the database, and one is created.
    """
    db = proteinnetworks.database.Database(password="bla")
    partitionArgs = {
        'pdbref': '1ubq',
        'N': 10,
        'edgelistid': ObjectId('58dbe03fef677d54224a01da'),
        'detectionmethod': 'Infomap',
        'r': -1,
        "database": db
    }
    partition = proteinnetworks.partition.Partition(**partitionArgs)  # Tested by partition tests
    superNetwork = proteinnetworks.insight.SuperNetwork(partition)
    # Need to check that the partition is as expected
    assert superNetwork


"""
tests for getModifiedJaccard()

inputs:
An expected Array and a generated Array (both numpy arrays)

returns:
the modified jaccard between the two arrays.

tests:
expectedArray and/or generatedArray not numpy arrays (e.g. lists or strings)
expectedArray and/or generatedArray of length 0

the case with overlap of one domain
the case with some overlap of multiple domains
the case with total overlap
multiple expected domains
"""

def test_getmodifiedjaccard_invalidinputs_wrongtype_list():
    """
    Test that non-numpy arrays are rejected
    """
    expected = [1]*40 + [2]*20 + [1]*40
    generated = [1]*40 + [2]*20 + [1]*40
    with pytest.raises(TypeError):
        jaccard = proteinnetworks.insight.getModifiedJaccard(expected, generated)
    


def test_getmodifiedjaccard_invalidinputs_wrongtype_string():
    """
    Second test that numpy arrays of non-ints (in this case, strings) are rejected
    """
    expected = np.asarray(["a"]*40 + ["b"]*20 + ["a"]*40)
    generated = np.asarray(["a"]*40 + ["b"]*20 + ["c"]*40)
    with pytest.raises(TypeError):
        jaccard = proteinnetworks.insight.getModifiedJaccard(expected, generated)

def test_getmodifiedjaccard_invalidinputs_wrongtype_floats():
    """
    Second test that numpy arrays of non-ints (in this case, floats) are rejected
    """
    expected = np.asarray([0.5]*40 + [1]*20 + [0.5]*40)
    generated = np.asarray([0.5]*40 + [1.0]*20 + [1.5]*40)
    with pytest.raises(TypeError):
        jaccard = proteinnetworks.insight.getModifiedJaccard(expected, generated)



def test_getmodifiedjaccard_invalidinputs_emptyarrays():
    """
    Test that zero-length numpy arrays are rejected
    """
    expected = np.asarray([])
    generated = np.asarray([])
    with pytest.raises(ValueError):
        jaccard = proteinnetworks.insight.getModifiedJaccard(expected, generated)

def test_getmodifiedjaccard_invalidinputs_differentarrays():
    """
    Test that different-length inputs are rejected
    """
    expected = np.asarray([1]*40 + [2]*20 + [1]*40)
    generated = np.asarray([1]*40 + [2]*20)
    with pytest.raises(ValueError):
        jaccard = proteinnetworks.insight.getModifiedJaccard(expected, generated)


def test_getmodifiedjaccard_perfectoverlap():
    """
    Check that if the PFAM array has perfect overlap with one domain, a score of 1.0 is returned. 
    """
    expected = np.asarray([1]*40 + [2]*20 + [1]*40)
    generated = np.asarray([1]*40 + [2]*20 + [3]*20 + [4]*20)
    jaccard = proteinnetworks.insight.getModifiedJaccard(expected, generated)
    assert jaccard == 1

def test_getmodifiedjaccard_partialoverlap_single_domains():
    """
    Check that if a PFAM array is a subset of a community, a score of <1.0 is returned.
    """
    expected = np.asarray([1]*40 + [2]*20 + [1]*40)
    generated = np.asarray([1]*40 + [2]*30 + [3]*10 + [4]*20)
    jaccard = proteinnetworks.insight.getModifiedJaccard(expected, generated)
    # intersection of size 20, union of size 30
    assert jaccard == 2/3



def test_getmodifiedjaccard_partialoverlap_multiple_domains():
    """
    Check that if a PFAM array is a subset of a community, a score of <1.0 is returned.
    """
    expected = np.asarray([1]*40 + [2]*20 + [1]*40)
    generated = np.asarray([1]*40 + [2]*10 + [3]*10 + [4]*40)
    jaccard = proteinnetworks.insight.getModifiedJaccard(expected, generated)
    # mean overlap is 0.5
    assert jaccard == 1/2


def test_getmodifiedjaccard_nopfamdomain():
    """
    Check that if the PFAM array is all 1s (i.e. no PFAM domains) an error is thrown.
    """
    expected = np.asarray([1]*40)
    generated = np.asarray([1]*20 + [2]*20)
    with pytest.raises(ValueError):
        jaccard = proteinnetworks.insight.getModifiedJaccard(expected, generated)
    



"""
Tests for generateNullModel

given a test partition, generate a partition with the same number of inter-community boundaries
and the same total number of communities

returns a numpy array (hopefully)

tests:
expectedArray not a numpy array (e.g. lists or strings)
expectedArray of length 0
the case with unit-length communities
the case with normal communities

check return is a numpy array.
"""

def test_generatenullmodel_invalidinput_list():
    """Check that lists are rejected."""
    expected = [1]*40
    with pytest.raises(TypeError):
        array = proteinnetworks.insight.generateNullModel(expected)
        

def test_generatenullmodel_invalidinput_string():
    """Check that arrays of strings are rejected."""
    expected = np.asarray(["bla"]*40)
    with pytest.raises(TypeError):
        array = proteinnetworks.insight.generateNullModel(expected)

def test_generatenullmodel_invalidinput_float():
    """Check that arrays of floats are  rejected."""

    expected = np.asarray([1.5]*40)
    with pytest.raises(TypeError):
        array = proteinnetworks.insight.generateNullModel(expected)

def test_generatenullmodel_invalidinput_zerolengtharray():
    """Check that zero-length arrays are rejected."""
    expected = np.asarray([])
    with pytest.raises(ValueError):
        array = proteinnetworks.insight.generateNullModel(expected)

def test_generatenullmodel_allcommunitiessizeone():
    expected = np.asarray(range(1,41))
    array = proteinnetworks.insight.generateNullModel(expected)
    assert len(set(array)) == 40
    numBoundaries = -1
    prevI = -1
    for i in array:
        if i != prevI:
            numBoundaries += 1
        prevI = i
    assert numBoundaries == 39
 
def test_generatenullmodel_singlecommunity():
    expected = np.asarray([1]*40)
    array = proteinnetworks.insight.generateNullModel(expected)
    assert len(set(array)) == 1
    numBoundaries = -1
    prevI = -1
    for i in array:
        if i != prevI:
            numBoundaries += 1
        prevI = i
    assert numBoundaries == 0


def test_generatenullmodel_normalcommunities():
    expected = np.asarray([1]*20 + [2]*20 + [3]*20 )
    array = proteinnetworks.insight.generateNullModel(expected)
    assert len(set(array)) == 3
    numBoundaries = -1
    prevI = -1
    for i in array:
        if i != prevI:
            numBoundaries += 1
        prevI = i
    assert numBoundaries == 2

def test_generatenullmodel_checkreturntype():
    expected = np.asarray([1]*40)
    expected = np.asarray([1]*20 + [2]*20 + [3]*20 )
    array = proteinnetworks.insight.generateNullModel(expected)
    assert type(array) == np.ndarray

def test_generatenullmodel_invalidinput_communities_start_from_one():
    """Check that the communities are labelled from 1 to N, without gaps"""
    expected = np.asarray([0]*5+[2]*5)
    with pytest.raises(ValueError):
        array = proteinnetworks.insight.generateNullModel(expected)



"""
tests for getMCS.

Inputs -> two networkx graphs

Outputs -> a smaller graph


Test:
- Invalid input
- Isomorphic graphs
- Graphs of the same size
- Graphs of different sizes
- Graphs with only one node
- Disconnected graphs
"""

def test_getmcs_invalid_input():
    """Test that inputs that aren't networkx undirected graphs are rejected.""" 
    input1 = [[1,2], [2,3], [1,3]]
    input2 = "bla"
    input1 = nx.DiGraph(input1)
    with pytest.raises(TypeError):
        mcs = proteinnetworks.insight.getMCS(input1, input2)



def test_getmcs_isomorphic_graphs():
    input1 = [[1,2], [2,3], [1,3]] # triangle
    input2 = [[2,3], [3,4], [4,2]] # triangle, differently labelled

    input1 = nx.Graph(input1)
    input2 = nx.Graph(input2)
    mcs = proteinnetworks.insight.getMCS(input1, input2)

    assert nx.is_isomorphic(mcs, input1) and nx.is_isomorphic(mcs, input2)

def test_getmcs_perfect_subgraph():

    input1 = [[1,2], [2,3], [1,3]] # triangle
    input2 = [[2,3], [3,4], [4,2], [2,5]] # triangle with an extra node

    input1 = nx.Graph(input1)
    input2 = nx.Graph(input2)
    mcs = proteinnetworks.insight.getMCS(input1, input2)
    assert nx.is_isomorphic(mcs, input1) and not nx.is_isomorphic(mcs, input2)

def test_getmcs_single_node_graph():
    input1 = [[1,2], [2,3], [1,3]] # triangle

    input1 = nx.Graph(input1)
    input2 = nx.Graph()
    input2.add_node(1)
    mcs = proteinnetworks.insight.getMCS(input1, input2)
    assert nx.is_isomorphic(mcs, input2) and not nx.is_isomorphic(mcs, input1)
    assert mcs.number_of_nodes() == 1

def test_getmcs_disconnected_graphs():
    input1 = [[1,2], [2,3], [1,3]] # triangle
    input2 = [[2,3], [3,4], [4,2], [5,6], [6,7], [7,5]] # two triangles
    input1 = nx.Graph(input1)
    input2 = nx.Graph(input2)
    mcs = proteinnetworks.insight.getMCS(input1, input2)
    assert nx.is_isomorphic(mcs, input1) and not nx.is_isomorphic(mcs, input2)



"""
Tests for getZscore

inputs -> two arrays & a number of trials
Output -> a float giving significance

We expect single-community and unit-community partitions to have significance zero (I think)

Tests:

Bad input (negative numTrials)

Single community comparison
Unit community comparison
Normal case comparison

FIXME any what circumstances will this be negative?

"""

def test_getzscore_invalid_number_of_trials():
    """Test that a negative number of trials is rejected."""
    expected = np.asarray([1]*40 + [2]*20 + [1]*40)
    generated = np.asarray([1]*40 + [2]*10 + [3]*10 + [4]*40)
    with pytest.raises(ValueError):
        score = proteinnetworks.insight.getZScore(expected, generated, numTrials=-100)
    pass

def test_getzscore_single_community():
    expected = np.asarray([1]*40 + [2]*20 + [1]*40)
    generated = np.asarray([1]*100)
    score = proteinnetworks.insight.getZScore(expected, generated)
    assert score == 0

def test_getzscore_unit_community():
    expected = np.asarray([1]*40 + [2]*20 + [1]*40)
    generated = np.asarray(range(1,101))
    score = proteinnetworks.insight.getZScore(expected, generated)
    assert score == 0

def test_getzscore_normal_communities():
    expected = np.asarray([1]*40 + [2]*20 + [1]*40)
    generated = np.asarray([1]*40 + [2]*20 + [3]*20 + [4]*20)
    score = proteinnetworks.insight.getZScore(expected, generated)
    assert score > 0

def test_getzscore_bad_communities():

    # we expect most random guesses to place the community barrier closer to the we generated
    expected = np.asarray([1]*60 + [2]*40) # + [1]*20)
    generated = np.asarray([1]*5 + [2]*95) # + [3]*15 + [4]*35)
    score = proteinnetworks.insight.getZScore(expected, generated, numTrials=1000)
    assert score < 0



"""
Tests for getShannonEntropy

inputs -> a partition  (assuming labelled [1,m])
outputs -> the shannon entropy,
H(A) = - sum_i ( n_i/N * log(n_i/N).

Tests:
- invalid input (anything not an array of numbers ranging from 1 to m without gaps)
- all nodes in their own community
- all nodes in the same community
- "normal" community structure  
"""

def test_getshannonentropy_invalid_inputs():
    """Test that an array not containing [1,M] is rejected."""
    testarray = [-1]*5 + [2]*5 +[4]*5
    with pytest.raises(ValueError):
        H = proteinnetworks.insight.getShannonEntropy(testarray)

def test_getshannonentropy_single_community():
    """Test the limiting case of all nodes in one community."""
    testarray = [1]*100
    H = proteinnetworks.insight.getShannonEntropy(testarray)
    assert H==0

def test_getshannonentropy_unit_community():
    """Test the limiting case of all nodes in their own community."""
    testarray = range(1,101)
    H = proteinnetworks.insight.getShannonEntropy(testarray)
    assert math.isclose(H,-math.log(1/100))

def test_getshannonentropy_normal_community():
    """Test a traditional community structure."""
    testarray = [1]*10+[2]*10
    H = proteinnetworks.insight.getShannonEntropy(testarray)
    assert math.isclose(H,-math.log(1/2))



"""
tests for getMutualInfo

inputs -> two partitions (numpy arrays, labels in [1,m])
outputs -> mutual information, should always >=0 and < the average Shannon entropy.

tests:
- on inputs (check proper labelling)

- all nodes in same community
- all nodes in different communities
- matching communities
- completely disparate communities
"""
def test_getmutualinfo_invalid_inputs_labels():
    """Test that improperly labelled arrays are rejected.""" 
    testarray1 = [-1]*5 + [2]*5 +[4]*5
    testarray2 = [-1]*5 + [2]*5 +[4]*5

    with pytest.raises(ValueError):
        I = proteinnetworks.insight.getMutualInfo(testarray1, testarray2)

def test_getmutualinfo_invalid_inputs_lengths():
    """Test that different length arrays will be rejecteed."""
    testarray1 = [1]*5 + [2]*5 +[3]*5
    testarray2 = [1]*5 + [2]*5 

    with pytest.raises(TypeError):
        I = proteinnetworks.insight.getMutualInfo(testarray1, testarray2)

def test_getmutualinfo_single_community():
    """Test that single communities have I=0."""
    testarray1 = [1]*100
    testarray2 = [1]*100
    I = proteinnetworks.insight.getMutualInfo(testarray1, testarray2)
    assert I==0

def test_getmutualinfo_unit_community():
    """Test that unit communities have I= log(N)."""
    testarray1 = list(range(1,101))
    testarray2 = list(range(1,101))
    I = proteinnetworks.insight.getMutualInfo(testarray1, testarray2)
    assert math.isclose(I,math.log(100))


def test_getmutualinfo_matching_communities():
    """Test that matching bipartitions have I=log(N).""" 
    testarray1 = [1]*10+[2]*10
    testarray2 = [1]*10+[2]*10
    I = proteinnetworks.insight.getMutualInfo(testarray1, testarray2)
    assert math.isclose(I,math.log(2))


"""
tests for getNMI

input -> two partitions (invalid inputs will be caught by other functions)
output -> a number that should always be between 0 and 1.
"""

def test_getnmi_perfect_match():
    """Test that perfectly matching communities have NMI=1."""
    testarray1 = [1]*10+[2]*10
    testarray2 = [1]*10+[2]*10
    nmi = proteinnetworks.insight.getNMI(testarray1, testarray2)
    assert nmi == 1

def test_getnmi_perfect_match():
    """Test that random communities have NMI between 0 and 1."""
    numberOfTrials = 100
    for i in range(numberOfTrials):
        arraySize = np.random.randint(2,300)
        numberOfCommunites = np.random.randint(3,20)
        randomPartition1 = []
        randomPartition2 = []
        i=1
        while len(randomPartition1) < arraySize:
            communitySize = np.random.randint(1, arraySize/2+1)
            randomPartition1 += [i]*communitySize
            i+=1
        randomPartition1 = randomPartition1[:arraySize]
        i=1
        while len(randomPartition2) < arraySize:
            communitySize = np.random.randint(1, arraySize/2+1)
            randomPartition2 += [i]*communitySize
            i+=1
        randomPartition2 = randomPartition2[:arraySize]

        np.random.shuffle(randomPartition1)
        np.random.shuffle(randomPartition2)

        nmi = proteinnetworks.insight.getNMI(randomPartition1, randomPartition2)
        assert nmi >= 0 and nmi <= 1


"""
tests for getConductanceFromPartition

inputs -> one Network, one Partition
outputs -> a List of floats


tests:
invalid inputs:
    - partition and network are for different systems

- disconnected network
- fully connected network
- random partitions on the same network?
"""




"""
tests for getConductanceFromNodeSubset

inputs -> a 1d numpy array of true/false values and a 2d adjacency matrix

outputs -> a float in [0,1]

tests:
invalid inputs:
    - malformed node_subset?
    - malformed adjacency matrix?
- disconnected adj_matrix
- fully connected adj_matrix
- random node subsets 
"""

"""
getModularityFromPartition
getModularityFromAdjacencyMatrix
edgelistToGraph
"""