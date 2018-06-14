"""Stores functionality related to the generation and analysis of edgelists."""

import numpy as np
import math
import networkx as nx
import warnings
import subprocess
import os
import matplotlib.pyplot as plt
from .database import Database
from .atomicradii import atomicRadii


class Network:
    """Holds a edgelist and its parameters, and offers network inspection methods."""

    def __init__(self,
                 pdbref,
                 edgelisttype,
                 hydrogenstatus,
                 scaling,
                 chainref=None,
                 database=None):
        """
        Initialise the edgelist with a given parameter set.

        Edgelist specified by:
            - scaling i.e cutoff
            - atomic / residue
            - status of hydrogen atoms
            - PDB reference
            - chain (whether the network describes a full protein or a chain)
        """
        self.scaling = scaling
        self.edgelisttype = edgelisttype
        self.hydrogenstatus = hydrogenstatus
        self.pdbref = pdbref
        self.chainref = chainref
        # Try to connect to the database
        if database:
            self.database = database
        else:
            print("no database provided: using temporary store")
            self.database = Database(local=True)
        # Attempt to extract the edgelist matching the given params
        doc = self.database.extractEdgelist(pdbref, edgelisttype,
                                            hydrogenstatus, scaling, chainref)
        if doc:
            self.edgelist = doc['data']
            self.edgelistid = doc['_id']
            print("edgelist found")
        else:
            print("no edgelist fitting those parameters found: generating")
            edgelist = self.generateEdgelist(pdbref, edgelisttype,
                                             hydrogenstatus, scaling, chainref)
            self.edgelist = edgelist
            self.edgelistid = self.database.depositEdgelist(
                pdbref, edgelisttype, hydrogenstatus, scaling, edgelist,
                chainref)

    def getAdjacencyMatrix(self):
        """Return the adjacency matrix as a numpy array."""
        n = max([max(i, j) for i, j, k in self.edgelist])
        adj = np.zeros((n, n), dtype=int)

        for edge in self.edgelist:
            # NB this requires integer weights
            i, j, weight = [int(x) for x in edge]
            adj[i - 1, j - 1] += weight
            adj[j - 1, i - 1] += weight
        return adj

    def generateEdgelist(self,
                         pdbref,
                         edgelisttype,
                         hydrogenstatus,
                         scaling,
                         chainref=None):
        r"""
        Generate the edgelist using the supplied parameters.

        The given pdbref is read in from the database (if it exists) else an
        attempt is made to acquire it from the web. A network is then generated in
        which atoms correspond to nodes, and edges are generated such that:
        $ A_{ij} = = 1 - \frac{|d_{ij}|}{c_{ij}} $

        Where $ c_{ij} = s(r_i + r_j) $, and $ r_i $ is the atomic radius of atom i.
        s is here the "scaling".

        FIXME this only currently works for single-atom elements in the pdb file (due to HAAD)
        FIXME I should integrate HAAD.
        FIXME I should sort out STRIDE

        """
        edges = []
        assert hydrogenstatus == "noH"  # for now
        # TODO HYDROGENSTATUS STUFF GOES HERE
        # if hydrogenstatus :
        #     proc = subprocess.run(["haad", filename], stderr= subprocess.DEVNULL)

        # if proc.returncode == -11:
        #     print("what a janky code. SIGSEGV caught.")
        #     sys.exit(1)
        #     # HAAD generates a *.pdb.h file, in which the positions of the hydrogens have
        #     # been added and all non-ATOM files (and the element info) stripped out.
        #     filename = filename + ".h"

        pdbdata = self.database.extractPDBFile(pdbref)
        if not pdbdata:
            pdbdata = self.database.fetchPDBFileFromWeb(pdbref)
        positions, elements, residues = extractAtomicData(pdbdata, chainref)
        assert len(positions) == len(residues) == len(elements)

        # get matrix of square distances
        distance_squared = np.sum(
            (positions[:, np.newaxis, :] - positions[np.newaxis, :, :])**2,
            axis=-1)

        n = np.shape(positions)[0]

        if edgelisttype == "atomic":
            # Then use atoms as vertices
            for i in range(0, n):
                for j in range(0, i):
                    # distance = getDistance(positions, i, j)
                    cutoff = (
                        atomicRadii[elements[i]] + atomicRadii[elements[j]]
                    ) * scaling
                    # cutoff = cutoffs[i,j]
                    if distance_squared[i, j] < cutoff * cutoff:
                        weight = (cutoff - math.sqrt(distance_squared[i, j])
                                  ) / cutoff
                        edges.append([i + 1, j + 1, weight])

        elif edgelisttype == "residue":
            # use the residues as vertices
            edgeList = {}
            for i in range(0, n):
                for j in range(0, i):
                    cutoff = (
                        atomicRadii[elements[i]] + atomicRadii[elements[j]]
                    ) * scaling
                    if distance_squared[i, j] < cutoff * cutoff:
                        res1, res2 = residues[i], residues[j]
                        if res1 != res2:
                            if not (res1, res2) in edgeList:
                                edgeList[(res1, res2)] = 1
                            else:
                                edgeList[(res1, res2)] += 1

            # Push to a list and sort by first value
            edges = []
            for row, weight in edgeList.items():
                i, j = row
                edges.append([i, j, weight])
            edges.sort()

        return edges

    def draw(self):
        """Draw the edgelist using NetworkX."""
        G = nx.Graph()
        for i, j, weight in self.edgelist:
            G.add_edge(i, j, weight=weight)

        pos = nx.spring_layout(G)
        fig, ax = plt.subplots(figsize=(5, 5))

        # Suppress MPL's complaining, as it's a NetworkX problem.
        warnings.filterwarnings("ignore")
        nx.draw(G, pos=pos, node_color="grey")
        ax.set_title("Network for {}".format(self.pdbref))
        plt.show()

    def getNetwork(self):
        """Return a NetworkX Graph object."""
        G = nx.Graph()
        for i, j, weight in self.edgelist:
            G.add_edge(i, j, weight=weight)
        return G

    def plotPymolNetworkStructure(self, outputPng=False):
        """
        Plot the network structure of the protein using PyMol.#

        TODO this only really works for atomic networks
        """

        # Work out whether the given edgelist is contact or atomic
        edgelisttype = self.database.extractDocumentGivenId(
            self.edgelistid)['edgelisttype']
        if edgelisttype == "residue":
            selector = "resi"
        elif edgelisttype == "atomic":
            selector = "index"

        # Write the pdb file out as a temp file for PyMol FIXME
        pdb = self.database.extractPDBFile(self.pdbref)
        if not pdb:
            pdb = self.database.fetchPDBFileFromWeb(self.pdbref)
        with open("temp.pdb", mode='w') as flines:
            flines.write("\n".join(pdb))

        pymolScript = "load temp.pdb, {0}".format(self.pdbref)
        pymolScript += "\n"
        if edgelisttype == "residue":
            pymolScript += "remove name ! ca\n"

        pymolScript += """
#formatting
remove solvent
hide all
show spheres
set sphere_scale, 0.25, (all)
set stick_radius=0.1
unbond (all), (all)
show sticks
set antialias = on
set depth_cue = 1
set specular = 1
set surface_quality = 1
set stick_quality = 15
set sphere_quality = 2
alter (all), b=1.0
set ray_trace_mode, 1
bg_color white
"""
        for node1, node2, weight in self.edgelist:
            pymolScript += 'cmd.bond("{0} {1}", "( {0} {2})")\n'.format(
                selector, node1, node2)

        pymolScript += "rebuild\n"

        # If we are doing a single-chain analysis, cut out the other chains
        try:
            chainRef = self.database.extractDocumentGivenId(
                self.edgelistid)['chainref']
            pymolScript += f"""
select notGivenChain, ! chain {chainRef}
remove notGivenChain
zoom
"""

        except KeyError:
            pass

        if outputPng:
            pymolScript += f"""
set ray_trace_mode = 1
png {self.pdbref}.png, width=10cm, dpi=300, ray=1
"""

        with open("temp.pml", mode='w') as flines:
            flines.write(pymolScript)

        if not outputPng:
            subprocess.run(["pymol", "temp.pml"])
        else:
            # Run quietly
            subprocess.run(["pymol", "-c", "temp.pml"])
        os.remove("temp.pml")
        os.remove("temp.pdb")


def extractAtomicData(pdbdata, chainref=None):
    """
    Given a PDB file in the form of a list of lines, extract the atomic data.

    if chainref is "None":
        pull all ATOM records, and push the atomic positions, element, and
        residue number to three arrays.
    else:
        pull all ATOM records matching the chainref, and assert that the arrays
        to be returned are non-empty.
    """
    positions = []
    elements = []
    residues = []
    residueCounter = 0
    prevRes = 0
    if chainref is None:
        for line in pdbdata:
            if line.strip() == "ENDMDL":
                break
            linelist = line.rstrip()
            if linelist[0:4] == "ATOM":
                residueNumber = int(linelist[22:26].strip())
                if residueNumber != prevRes:
                    residueCounter += 1
                prevRes = residueNumber
                positions.append(
                    [linelist[30:38], linelist[38:46], linelist[46:54]])
                # elements.append(linelist[76:78].strip())
                elements.append(linelist[13].strip())
                residues.append(residueCounter)
        positions = np.asarray(positions, dtype=float)
        return positions, elements, residues
    else:
        for line in pdbdata:
            if line.strip() == "ENDMDL":
                break
            linelist = line.rstrip()
            if linelist[0:4] == "ATOM" and linelist[21] == chainref:
                residueNumber = int(linelist[22:26].strip())
                if residueNumber != prevRes:
                    residueCounter += 1
                prevRes = residueNumber
                positions.append(
                    [linelist[30:38], linelist[38:46], linelist[46:54]])
                # elements.append(linelist[76:78].strip())
                elements.append(linelist[13].strip())
                residues.append(residueCounter)
        positions = np.asarray(positions, dtype=float)
        assert (positions.any() and elements and residues)
        return positions, elements, residues
