"""
Functions for analysing the information content of the community structures.

Includes the SuperNetwork class, which is initialised by passing a Partition (which
contains a reference to the edgelist used).

The modified Jaccard for each level of the partition is calculated, and the level with the
best correspondence to the PFAM domains is chosen to generate a supernetwork.
"""
import numpy as np
import networkx as nx
import matplotlib.pyplot as plt
import warnings
import itertools
from .partition import Partition


class SuperNetwork:
    """
    A network generated from the community structure of the protein.

    Pull from the database if possible: otherwise generate anew.
    """

    def __init__(self, inputpartition):
        """Generate the network from an existing Partition."""
        # Get the input partition and edgelist
        self.pdbref = inputpartition.pdbref  # Save the details on the partition used
        self.database = inputpartition.database
        self.partitionid = inputpartition.partitionid

        # Attempt to extract the supernetwork matching the given params
        doc = self.database.extractSuperNetwork(self.pdbref, self.partitionid)

        if doc:
            self.data = doc['data']
            self.level = doc['level']
            # print("supernetwork found")
        else:
            partition = inputpartition.data
            edgelist = inputpartition.database.extractDocumentGivenId(
                inputpartition.edgelistid)['data']

            # Find the level of the partition (assuming this is Infomap) with the best Jaccard
            try:
                pfamDomains = np.asarray(
                    inputpartition.getPFAMDomainArray(), dtype=int)
            except ValueError:
                print("No PFAM entry -> cannot generate supernetwork")
                raise ValueError

            maxJaccard = -1
            maxI = -1
            for i, col in enumerate(partition):
                jaccard = getModifiedJaccard(
                    pfamDomains, np.asarray(
                        col, dtype=int))
                print("Level {} has Jaccard {}".format(i, jaccard))
                if jaccard > maxJaccard:
                    maxJaccard = jaccard
                    maxI = i
            print("Using level {}".format(maxI))
            self.level = maxI
            partition = partition[maxI]

            # Generate the supernetwork
            communityEdgeList = {}
            for i, j, _ in edgelist:
                com_i, com_j = partition[int(i) - 1], partition[int(j) - 1]
                if com_i != com_j:
                    if not (com_i, com_j) in communityEdgeList:
                        if (com_j, com_i) in communityEdgeList:
                            communityEdgeList[(com_j, com_i)] += 1
                        else:
                            communityEdgeList[(com_i, com_j)] = 1
                    else:
                        communityEdgeList[(com_i, com_j)] += 1

            communityEdgeListSorted = []
            for row, weight in communityEdgeList.items():
                i, j = row
                communityEdgeListSorted.append([i, j, weight])
            communityEdgeListSorted.sort()

            self.data = communityEdgeListSorted
            self.database.depositSuperNetwork(self.pdbref, self.partitionid,
                                              self.level, self.data)

    @classmethod
    def fromPartitionId(SuperNetwork, partitionid, database):
        """
        Given a database and a partitionid, generate the Partition class.

        Then generate the SuperNetwork as normal from the partition.
        FIXME: this is really very convoluted.
        """
        partitionDetails = database.extractDocumentGivenId(partitionid)

        if 'r' in partitionDetails:
            inputPartition = Partition(
                partitionDetails['pdbref'],
                partitionDetails['edgelistid'],
                partitionDetails['detectionmethod'],
                r=partitionDetails['r'],
                database=database)
        elif 'N' in partitionDetails:
            inputPartition = Partition(
                partitionDetails['pdbref'],
                partitionDetails['edgelistid'],
                partitionDetails['detectionmethod'],
                N=partitionDetails['N'],
                database=database)
        return SuperNetwork(inputpartition=inputPartition)

    def draw(self):
        """Draw the reduced edgelist using NetworkX."""
        G = nx.Graph()
        for i, j, weight in self.data:
            G.add_edge(i, j, weight=weight)

        pos = nx.spring_layout(G, k=10)
        fig, ax = plt.subplots(figsize=(5, 5))

        # Suppress MPL's complaining, as it's a NetworkX problem.
        warnings.filterwarnings("ignore")
        nx.draw(G, pos=pos, node_color="grey")
        ax.set_title("Community network for {}".format(self.pdbref))
        plt.show()

    def getIsomorphs(self):
        """Get all proteins in the database with an isomorphic supernetwork."""
        # Generate the NetworkX graph for the supernetwork
        G = nx.Graph()
        for i, j, weight in self.data:
            G.add_edge(i, j, weight=weight)

        # Get a cursor for all supernetworks in the database
        proteins = self.database.extractAllSuperNetworks(pdbref=self.pdbref)
        isomorphs = []
        for protein in proteins:
            G2 = nx.Graph()
            for i, j, weight in protein['data']:
                G2.add_edge(i, j, weight=weight)
            if nx.faster_could_be_isomorphic(G, G2) and nx.is_isomorphic(G,
                                                                         G2):
                isomorphs.append(protein['pdbref'])
        return isomorphs

    def getWeakIsomorphs(self, subset=None):
        """
        Get all proteins in the database with an weakly isomorphic supernetwork.

        Returns a list [self.pdbref, otherpdbref, simscore] for all proteins with
        a simscore > 0.5.

        If a subset of the supernetworks are given, this is used. (subset must be a numpy array)
        """
        # Generate the NetworkX graph for the supernetwork
        G = nx.Graph()
        for i, j, weight in self.data:
            G.add_edge(i, j)

        G = nx.convert_node_labels_to_integers(G)
        # Get a cursor for all supernetworks in the database

        if subset.any():
            proteins = subset
        else:
            proteins = self.database.extractAllSuperNetworks(pdbref=self.pdbref)
        weakIsomorphs = []
        for protein in proteins:
            G2 = nx.Graph()
            for i, j, weight in protein['data']:
                G2.add_edge(i, j)

            G2 = nx.convert_node_labels_to_integers(G2)
            # Get the maximum common subgraph for the two supernetworks
            try:
                MCS = getMCS(G, G2)
            except ValueError:
                continue
            if MCS:
                similarity = MCS.number_of_nodes() / (max(
                    G.number_of_nodes(), G2.number_of_nodes()))
            else:
                similarity = 0

            if similarity > 0.5:
                weakIsomorphs.append(
                    [self.pdbref, protein['pdbref'], str(similarity)])

        return weakIsomorphs


def getModifiedJaccard(expectedArray, generatedArray):
    """
    A scoring function for each PFAM domain in a protein.

    Requires:
    - The PDB file
    - The PFAM/PDB mapping
    - The .tree file (or other community structure)

    Scoring algorithm:

    For each domain:
        - Collect all the generated modules that overlap with the PFAM domain
        - Calculate the Jaccard index:
            J = | A ∩ B | / | A ∪ B |
        - Return the mean Jaccard for all generated modules, weighted by the intersection.

    The final score is the mean value over all domains.
    """
    numPFAMdomains = len(
        set(expectedArray))  # NB this include "1", the base counter
    jaccards = []
    for i in range(2, numPFAMdomains + 1):
        # Get the modules with some overlap.
        jaccard = []
        intersections = []
        overlappingModules = set(generatedArray[expectedArray == i])
        for j in overlappingModules:
            intersection = np.count_nonzero(
                np.logical_and(generatedArray == j, expectedArray == i))
            union = np.count_nonzero(
                np.logical_or(generatedArray == j, expectedArray == i))
            jaccard.append(intersection / union)
            intersections.append(intersection)

        # weight the terms according to the overlap proportion.
        jaccard = [
            x * y / sum(intersections) for x, y in zip(jaccard, intersections)
        ]
        jaccard = sum(jaccard)
        jaccards.append(jaccard)
    return np.mean(jaccards)


def getMCS(G1, G2):
    """Take two networkx graphs, return the MCS as a networkx graph."""
    # Let G1 be the smaller graph
    if G1.number_of_nodes() > G2.number_of_nodes():
        temp = G2
        G2 = G1
        G1 = temp

    N_G1 = G1.number_of_nodes()
    N_G2 = G2.number_of_nodes()
    if N_G2 > 25:
        raise ValueError("Graph is too large")
    nodelist_G1 = list(range(N_G1))
    nodelist_G2 = list(range(N_G2))
    for i in range(N_G1, 0, -1):
        # Get all choose(N_G1, i) possible selections of [1... N_G1]
        # print(i)
        for subgraph_G1_nodelist in itertools.combinations(nodelist_G1, i):
            subgraph_G1 = G1.subgraph(subgraph_G1_nodelist)
            # Check whether subgraph_G1 is isomorphic to any subgraph of the same size in G2
            for subgraph_G2_nodelist in itertools.combinations(nodelist_G2, i):
                subgraph_G2 = G2.subgraph(subgraph_G2_nodelist)
                if nx.is_isomorphic(subgraph_G1, subgraph_G2):
                    return nx.Graph(subgraph_G1)
