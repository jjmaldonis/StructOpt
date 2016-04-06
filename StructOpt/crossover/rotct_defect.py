import random
import numpy
from ase import Atom, Atoms
from StructOpt.tools.find_defects import find_defects
from StructOpt.tools.position_average import position_average
from StructOpt.tools.shift_atoms import shift_atoms
from StructOpt.io import write_xyz

def rotct_defect(ind1, ind2, Optimizer):
    """Rotate atoms cut and splice
    Translates atoms to center of positions first
    Rotates atoms randomly around center of mass and cuts with xy plane
    Maintains number of atoms
    Maintains concentration of atoms
    Returns individuals to standard positions at end (un-rotates)
    """

    if 'CX' in Optimizer.debug:
        debug = True
    else:
        debug = False
    Optimizer.output.write('Rotate Cut/Splice Cx for defects between individual {} and individual {}\n'.format(repr(ind1.index), repr(ind2.index)))

    # Perserve starting conditions of individual
    indi1 = ind1[0].copy()
    indi2 = ind2[0].copy()

    # Translate individuals so COP is at (0, 0, 0)
    if Optimizer.structure == 'Defect':
        # Identify center of positions for defect structure
        indi1c, indi1b, vacant1, swap1, stro1 = find_defects(indi1, Optimizer.solidbulk, 0)
        com1 = position_average(indi1c)
        indi1 = shift_atoms(indi1, com1)
        trans = [-p for p in numpy.maximum.reduce(indi1.get_cell())]
        indi1.translate(trans)
        # Do the same for second individual
        indi2c, indi2b, vacant2, swap2, stro2 = find_defects(indi2, Optimizer.solidbulk, 0)
        com2 = position_average(indi2c)
        indi2 = shift_atoms(indi2, com2)
        indi2.translate(trans)
    else:
        com1 = indi1.get_center_of_mass()
        indi1.translate(-1*com1)
        com2 = indi2.get_center_of_mass()
        indi2.translate(-1*com2)

    # Select random axis, random angle, and random position and rotate individuals
    n = 0
    while n < 10:
        rax = random.choice(['x', '-x', 'y', '-y', 'z', '-z'])
        rang = random.random()*90
        indi1.rotate(rax, a=rang, center=[0, 0, 0], rotate_cell=False)
        # Search for atoms in individual 1 that are above the xy plane
        group1 = Atoms(cell=ind1[0].get_cell(), pbc=ind1[0].get_pbc())
        indices1 = []
        for one in indi1:
            if one.position[2] >= 0:
                group1.append(one)
                indices1.append(one.index)
        if len(group1) > 2 and len(group1) < len(indi1):
            break
        else:
            n += 1
            indi1.rotate(rax, a=-1*rang, center=[0, 0, 0], rotate_cell=False)
    indi2.rotate(rax, a = rang, center = [0, 0, 0], rotate_cell = False)

    if debug:
        print('Group1 size = ', len(group1))
        print('Position = ', [0, 0, 0])
        print('Angle = ', rang)
        print('Axis = ', rax)
        print('Number of tries = ', n+1)

    if len(group1) != 0:
        # Apply concentration forcing if needed
        group2 = Atoms(cell=ind2[0].get_cell(), pbc=ind2[0].get_pbc())
        indices2 = []
        dellist = []
        for one in indi2:
            if one.position[2] >= 0:
                group2.append(one)
                indices2.append(one.index)

        if Optimizer.forcing == 'Concentration':
            symlist = list(set(indi1.get_chemical_symbols()))
            seplist = [[atm for atm in group2 if atm.symbol == sym] for sym in symlist]
            group2n = Atoms(cell=group2.get_cell(), pbc=group2.get_pbc())
            indices2n = []
            dellist = []
            for one in group1:
                sym1 = one.symbol
                listpos = [i for i, s in enumerate(symlist) if s == sym1][0]
                if len(seplist[listpos]) > 0:
                    pos = random.choice(range(len(seplist[listpos])))
                    group2n.append(seplist[listpos][pos])
                    indices2n.append(indices2[seplist[listpos][pos].index])
                    del seplist[listpos][pos]
                else:
                    dellist.append(one.index)
            if len(dellist) != 0:
                dellist.sort(reverse=True)
                for one in dellist:
                    del group1[one]
                    del indices1[one]
            indices2 = indices2n
            group2 = group2n.copy()
        else:
            dellist = []
            while len(group2) < len(group1)-len(dellist):
                # Too many atoms in group 1
                dellist.append(random.choice(group1).index)
            if len(dellist) != 0:
                dellist.sort(reverse=True)
                for one in dellist:
                    del group1[one]
                    del indices1[one]
            dellist = []
            while len(group1) < len(group2)-len(dellist):
                # Too many atoms in group 2
                dellist.append(random.choice(group2).index)
            if len(dellist) != 0:
                dellist.sort(reverse = True)
                for one in dellist:
                    del group2[one]
                    del indices2[one]

        other2 = Atoms(cell = ind2[0].get_cell(), pbc = ind2[0].get_pbc())
        for one in indi2:
            if one.index not in indices2:
                other2.append(one)
        other1 = Atoms(cell = ind1[0].get_cell(), pbc = ind1[0].get_pbc())
        for one in indi1:
            if one.index not in indices1:
                other1.append(one)
        indi1 = group2.copy()
        indi1.extend(other1)
        indi2 = group1.copy()
        indi2.extend(other2)

        # DEBUG: Write crossover to file
        if debug:
            write_xyz(Optimizer.debugfile, group1, 'group1')
            write_xyz(Optimizer.debugfile, other1, 'other1')
            write_xyz(Optimizer.debugfile, group2, 'group2')
            write_xyz(Optimizer.debugfile, other2, 'other2')
            print 'Length of group1 = ', len(group1), 'Length of group2', len(group2)

        # DEBUG: Check structure of atoms exchanged
        for sym, c, m, u in Optimizer.atomlist:
            nc = len([atm for atm in indi1 if atm.symbol == sym])
            Optimizer.output.write('CX ROTCT_Defect: Individual 1 contains {} {} atoms\n'.format(repr(nc), repr(sym))
            nc = len([atm for atm in indi2 if atm.symbol == sym])
            Optimizer.output.write('CX ROTCT_Defect: Individual 2 contains {} {} atoms\n'.format(repr(nc), repr(sym))

        if Optimizer.forcing != 'Concentration':
            for i in range(len(Optimizer.atomlist)):
                atms1 = [inds for inds in indi1 if inds.symbol == Optimizer.atomlist[i][0]]
                atms2 = [inds for inds in indi2 if inds.symbol == Optimizer.atomlist[i][0]]
                if len(atms1) == 0:
                    if len(atms2) == 0:
                        indi1[random.randint(0, len(indi1)-1)].symbol == Optimizer.atomlist[i][0]
                        indi2[random.randint(0, len(indi2)-1)].symbol == Optimizer.atomlist[i][0]
                    else:
                        indi1.append(atms2[random.randint(0, len(atms2)-1)])
                        indi1.pop(random.randint(0, len(indi1)-2))
                else:
                    if len(atms2) == 0:
                        indi2.append(atms1[random.randint(0, len(atms1)-1)])
                        indi2.pop(random.randint(0, len(indi2)-2))
        indi1.rotate(rax, a = -1*rang, center = [0, 0, 0], rotate_cell = False)
        indi2.rotate(rax, a = -1*rang, center = [0, 0, 0], rotate_cell = False)

        if Optimizer.structure == 'Defect':
            trans = [-p for p in trans]
            indi1.translate(trans)
            indi2.translate(trans)
            indi1 = shift_atoms(indi1, [-p for p in com1])
            indi2 = shift_atoms(indi2, [-p for p in com2])
        else:
            indi1.translate(com1)
            indi2.translate(com2)

        # DEBUG: Check structure and number of atoms in crystal
        if Optimizer.structure == 'Defect':
            solid1 = Atoms()
            solid1.extend(indi1)
            solid1.extend(ind1.bulki)
            solid2 = Atoms()
            solid2.extend(indi2)
            solid2.extend(ind2.bulki)
            for sym, c, m, u in Optimizer.atomlist:
                nc = len([atm for atm in solid1 if atm.symbol == sym])
                Optimizer.output.write('CX ROTCT_Defect: Defect 1 configuration contains {} {} atoms\n'.format(repr(nc), repr(sym))
                nc = len([atm for atm in solid2 if atm.symbol == sym])
                Optimizer.output.write('CX ROTCT_Defect: Defect 2 configuration contains {} {} atoms\n'.format(repr(nc), repr(sym))
        if debug: Optimizer.output.flush()
        #pdb.set_trace()
        ind1[0] = indi1
        ind2[0] = indi2

    return ind1, ind2
