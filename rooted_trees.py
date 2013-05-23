import numpy as np
from sympy import factorial, sympify, Rational
from utils import permutations

leaf = ()

#=====================================================
class RootedTree(tuple):
#=====================================================
    r"""
        A rooted tree is a directed acyclic graph with one node, which
        has no incoming edges, designated as the root.
        Rooted trees are useful for analyzing the order conditions of 
        multistage numerical ODE solvers, such as Runge-Kutta methods 
        and other general linear methods.

        The trees are represented as strings, using one of the notations
        introduced by Butcher (the third column of Table 300(I) of
        Butcher's text).  The character 'T' is used in place of $\\tau$ 
        to represent a vertex, and braces '{ }' are used instead of brackets 
        '[ ]' to indicate that everything inside the braces
        is joined to a single parent node.  Thus the first four trees are:

        'T', '{T}', '{T^2}', {{T}}'

        These can be generated using the function list_trees(), which
        returns a list of all trees of a given order::

            >>> from nodepy import *
            >>> for p in range(4): print rt.list_trees(p)
            ['']
            ['T']
            ['{T}']
            ['{{T}}', '{T^2}']
            
        Note that the tree of order 0 is indicated by an empty string.
        
        If the tree contains an edge from vertex A to vertex B, vertex
        B is said to be a child of vertex A.
        A vertex with no children is referred to as a leaf.  

        .. warning::

            One important convention is assumed in the code; namely, that at each 
            level, leaves are listed first (before any other subtrees), 
            and if there are $n$ leaves, we write 'T^n'.
        
        .. note::

            Currently, powers cannot be used for subtrees; thus

            '{{T}{T}}'

            is valid, while

            '{{T}^2}' 

            is not.  This restriction may be lifted in the future.

        **Examples**::

            >>> from nodepy import rooted_trees as rt
            >>> tree=rt.RootedTree('{T^2{T{T}}{T}}')
            >>> tree.order()
            9
           >>> tree.density()
            144
            >>> tree.symmetry()
            2

        Topologically equivalent trees are considered equal::

            >>> tree2=RootedTree('{T^2{T}{T{T}}}')
            >>> tree2==tree
            True

        We can generate Python code to evaluate the elementary weight
        corresponding to a given tree for a given class of methods::

            >>> rk.elementary_weight_str(tree)
            'dot(b,dot(A,c)*dot(A,c*dot(A,c))*c**2)'

        **References**:  
            #. [butcher2003]_
            #. [hairer1993]_
    """
    def __init__(self,rep):
        """
            TODO:   - Check validity of strg more extensively
                    - Accept any leaf ordering, but convert it to our convention
                    - convention for ordering of subtrees?
        """
        if rep is tuple:
            self = rep
        elif rep is str:
            if any([strg[i] not in '{}T^1234567890' for i in range(len(strg))]):
                raise Exception('Not a valid rooted tree string (illegal character)')
            op,cl=strg.count('{'),strg.count('}')
            if op!=cl or (op+cl>0 and (strg[0]!='{' or strg[-1]!='}')):
                raise Exception('Not a valid rooted tree string')
            self=str_to_tuple(rep) # This still needs to be implemented

    def __str__(self):
        """
            Examples::

                >>> tree=rt.RootedTree( ((),(),((),((),))) )
                >>> print tree
                {T^2{T{T}}}
        """
        if self == (0,):
            return ''
        elif self == ():
            return 'T'
        nleaves = self.count( () )
        if nleaves > 1:
            leaves_str = 'T^'+str(nleaves)
        elif nleaves == 1:
            leaves_str = 'T'
        else:
            leaves_str = ''
        return '{'+leaves_str+''.join([str(RootedTree(tree)) for tree in self.nonleaf_subtrees()])+'}'

    def nonleaf_subtrees(self):
        """Return tuple of subtrees with leaves removed."""
        tree = list(self)
        while leaf in tree:
            tree.remove(leaf)
        return RootedTree(tree)


    def Dmap(self):
        """ 
        Butcher's function $D(t)$.  Represents differentiation.
        Defined by $D(t)$=0 except for D('T')=1.

        **Reference**: 
            #. [butcher1997]_
        """
        return self == ()

    def lamda(self,alpha,extraargs=[]):
        r""" 
            Computes Butcher's functional lambda on a given tree
            for the function alpha.  This is used to compute the
            product of two functions on trees.

            *INPUT*:

                * alpha -- a function on rooted trees
                * extraargs -- a list containing any additional arguments 
                  that must be passed to alpha

            *OUTPUT*:
                * tprod -- a list of trees [t1, t2, ...]
                * fprod -- a list of numbers [a1, a2, ...]

            The meaning of the output is that 
            $\\lambda(\\alpha,t)(\\beta)=a1*\\beta(t1)+a2*\\beta(t2)+...$ 

            **Examples**::

                >>> from nodepy import rt
                >>> tree = rt.RootedTree( ( (),((),)) )
                >>> print tree
                {T{T}}
                >>> tree.lamda(rt.Emap)
                ([(), (()), ((())), (()), ((), ()), ((()), ())], [1/2, 1, 1, 1/2, 1, 1])

            **Reference**: 
                [butcher2003]_ pp. 275-276
        """
        if self == (0,): return [None],[0]
        if self == ():   return [RootedTree( () )],[1]
        t,u=self._factor()
        print self, t, u, t*u==self
        if extraargs:
            l1,f1=t.lamda(alpha,*extraargs)
            l2,f2=u.lamda(alpha,*extraargs)
            alphau=alpha(u,*extraargs)
        else:
            l1,f1=t.lamda(alpha)
            l2,f2=u.lamda(alpha)
            alphau=alpha(u)
        tprod=l1
        fprod=[alphau*f1i for f1i in f1 if f1!=0]
        #FOIL:
        for i in range(len(l1)):
            if f1!=0:
                for j in range(len(l2)):
                    if f2!=0:
                        tprod.append(l1[i]*l2[j])
                        fprod.append(f1[i]*f2[j])
        return tprod,fprod

    def lamda_str(self,alpha,extraargs=[]):
        """
            Alternate version of lamda above, but returns a string.
            Hopefully we can get rid of this (and the other str functions)
            when SAGE can handle noncommutative symbolic algebra.
        """
        if not isinstance(extraargs,list): extraargs=[extraargs]
        if self=='': return [RootedTree('')],[0]
        if self=='T': return [RootedTree('T')],[1]
        t,u=self._factor()
        if extraargs:
            l1,f1=t.lamda_str(alpha,*extraargs)
            l2,f2=u.lamda_str(alpha,*extraargs)
            alphau=alpha(u,*extraargs)
        else:
            l1,f1=t.lamda_str(alpha)
            l2,f2=u.lamda_str(alpha)
            alphau=alpha(u)
        tprod=l1
        fprod=[str(f1i)+'*'+alphau for f1i in f1 if f1!=0]
        #FOIL:
        for i in range(len(l1)):
            if f1!=0:
                for j in range(len(l2)):
                    if f2!=0:
                        tprod.append(l1[i]*l2[j])
                        fprod.append(str(f1[i])+'*'+str(f2[j]))
        return tprod,fprod

    def _factor(self):
        """ 
            Returns two rooted trees, t and u, such that self=t*u.

            **Input**: 
                - self -- any rooted tree
            **Output**: 
                - t,u -- a pair of rooted trees whose product t*u is equal to self.

            **Examples**::

                >>> tree=RootedTree( ((),(),((),)) )
                >>> print tree
                {T^2{T}}
                >>> t,u=tree._factor()
                >>> print t
                {T{T}}
                >>> print u
                T
                >>> t*u==tree
                True

            .. note:: This function is typically only called by lamda().
        """
        if len(self) == 1:
            t = RootedTree( () )
            u = RootedTree(self[0])
        elif () in self:
            u = RootedTree( () )
            t = list(self)
            t.remove(())
            t = RootedTree(t)
        else:
            t = RootedTree(self[0])
            u = RootedTree(self[1:])
        return t,u

    def Gprod(self,alpha,beta,alphaargs=[],betaargs=[]):
        r""" 
            Returns the product of two functions on a given tree.

            INPUT:
                alpha, beta -- two functions on rooted trees
                               that return symbolic or numeric values
                alphaargs   -- a string containing any additional arguments 
                                that must be passed to function alpha
                betaargs    -- a string containing any additional arguments 
                                that must be passed to function beta

            OUTPUT:
                (alpha*beta)(self)
                i.e., the function that is the product (in G) of the
                functions alpha and beta.  Note that this product is
                not commutative.

            The product is given by

            $(\\alpha*\\beta)('')=\\beta('')$

            $(\\alpha*\\beta)(t) = \\lambda(\\alpha,t)(\\beta) + \\alpha(t)\\beta('')$

            .. note::
                Gprod can be used to compute products of more than two
                functions by passing Gprod itself in as beta, and providing
                the remaining functions to be multiplied as betaargs.

            **Examples**::

                >>> from nodepy import rt
                >>> tree = rt.RootedTree('{T{T}}')
                >>> tree.Gprod(rt.Emap,Dmap)
                1/2

            **Reference**: [butcher2003]_ p. 276, Thm. 386A 
        """
        trees,factors=self.lamda(alpha,*alphaargs)
        s=0
        for i in range(len(trees)):
            s+=factors[i]*beta(trees[i],*betaargs)
        s+=alpha(self,*alphaargs)*beta(RootedTree(None),*betaargs)
        return s

    def Gprod_str(self,alpha,beta,alphaargs=[],betaargs=[]):
        """ 
            Alternate version of Gprod, but operates on strings.
            Hopefully can be eliminated later in favor of symbolic
            manipulation.
        """
        trees,facs=self.lamda_str(alpha,*alphaargs)
        s=""
        for i in range(len(trees)):
            if facs[i]!=0:
                bet=beta(trees[i],*betaargs)
                if bet not in ['0','']:
                    if i>0: s+='+'
                    s+=str(facs[i])+"*"+bet
        bet=beta(RootedTree(""),*betaargs)
        if bet not in ['0','']:
            alph=alpha(self,*alphaargs)
            s+="+"+str(sympify(alph+'*'+bet))
        return s


    def _parse_subtrees(self):
        """ 
            Returns the number of leaves and a list of the subtrees,
            for a given rooted tree.

            OUTPUT:
                nleaves  -- number of leaves attached directly to the root
                subtrees -- list of non-leaf subtrees attached to the root

            The method can be thought of as returning what remains if the
            root of the tree is removed.  For efficiency, instead of
            returning possibly many copies of 'T', the leaves are just
            returned as a number.
        """
        nleaves = self.count( () )
        subtrees = list(self)
        while () in subtrees:
            subtrees.remove( () )
        return nleaves,tuple(subtrees)

    def list_equivalent_trees(self):
        """ 
            Returns a list of all strings (subject to our assumptions)
            equivalent to a given tree 

            INPUT: 
                self     -- any rooted tree
            OUTPUT:  
                treelist -- a list of all the 'legal' tree strings
                            that produce the same tree.

            The list of equivalent trees is obtained by taking all
            permutations of the (non-leaf) subtrees.
            This routine is used to test equality of trees.
        """
        nleaves,subtrees=self._parse_subtrees()
        if len(subtrees)==0: return [self]
        for i in range(len(subtrees)): subtrees[i]=str(subtrees[i])
        treelist = [RootedTree('{'+_powerString('T',nleaves,powchar='^')+
                    ''.join(sts)+'}') for sts in permutations(subtrees)]
        return treelist

    def __eq__(self,tree2):
        """
            Test equivalence of two rooted trees.
            Generates all 'legal' strings equivalent to the first
            tree, and checks whether the second is in that list.
        """
        if (self is None) and (tree2 is None):
            return True
        elif (self is None) or (tree2 is None):
            return False
        tree1 = list(self)
        tree2 = list(tree2)
        if len(tree1) != len(tree2):
            return False
        while len(tree1)>0:
            subtree = tree1[0]
            if tree1[0] in tree2:
                tree2.remove(subtree)
                tree1.remove(subtree)
            else: return False
        if len(tree2) == 0:
            return True
        else: return False


    def __mul__(self,tree2):
        """ 
            Returns Butcher's product: t*u is the tree obtained by
            attaching the root of u as a child to the root of t. 
            Note that u*t != t*u.
            See Butcher, pp. 138-139.
        """
        x = list(self)
        x.append(tree2)
        return RootedTree(tuple(x))

#=====================================================
#End of RootedTree class
#=====================================================

#=====================================================
def plot_all_trees(p,title='str'):
#=====================================================
    """ Plots all rooted trees of order p """
    import matplotlib.pyplot as pl
    forest=list_trees(p)
    nplots=len(forest)
    nrows=int(np.ceil(np.sqrt(float(nplots))))
    ncols=int(np.floor(np.sqrt(float(nplots))))
    if nrows*ncols<nplots: ncols=ncols+1
    for tree in forest:
        if title=='str': ttitle=tree
        else: ttitle=''
        tree.plot(nrows,ncols,forest.index(tree)+1,ttitle=ttitle)
    fig=pl.figure(1)
    pl.setp(fig,facecolor='white')
    return fig

#=====================================================
def list_trees(p,ind='all'):
#=====================================================
    """ 
    Returns rooted trees of order p.

    INPUT: 
    
        - p   -- order of trees desired
        - ind -- if given, returns a single tree corresponding to this index.
                Not very useful since the ordering isn't obvious.
                
    OUTPUT: list of all trees of order p (or just one, if ind is provided).
    
    Generates the rooted trees using Albrecht's 'Recursion 3'.

    **Examples**:

    Produce column of Butcher's Table 302(I)::

        >>> for i in range(1,11): 
        ...     forest=list_trees(i)
        ...     print len(forest)
        1
        1
        2
        4
        9
        20
        48
        115
        286
        719

    .. warning::

        This code is complete only up to order 10.  We need to extend it 
        by adding more subloops for p>10.

    TODO: Implement Butcher's formula (Theorem 302B) for the number
            of trees and determine to what order this is valid.

    **Reference**: [albrecht1996]_
    """

    if p==0: return [RootedTree('')]
    W=[[],[]] #This way indices agree with Albrecht
    R=[[],[]]
    R.append([RootedTree("{T}")])
    W.append([RootedTree("{{T}}")])
    for i in range(3,p):
        #Construct R[i]
        ps=_powerString("T",i-1,powchar="^")
        R.append([RootedTree("{"+ps+"}")])
        for w in W[i-1]:
            R[i].append(w)
        #Construct W[i]
        #l=0:
        W.append([RootedTree("{"+R[i][0]+"}")])
        for r in R[i][1:]:
            W[i].append(RootedTree("{"+r+"}"))
        for l in range(1,i-1): #level 1
            for r in R[i-l]:
                ps=_powerString("T",l,powchar="^")
                W[i].append(RootedTree("{"+ps+r+"}"))
        for l in range(0,i-3): #level 2
            for n in range(2,i-l-1):
                m=i-n-l
                if m<=n: #Avoid duplicate conditions
                    for Rm in R[m]:
                        lowlim=(m<n and [0] or [R[m].index(Rm)])[0]
                        for Rn in R[n][lowlim:]:
                            ps=_powerString("T",l,powchar="^")
                            W[i].append(RootedTree("{"+ps+Rm+Rn+"}"))
        for l in range(0,i-5): #level 3
            for n in range(2,i-l-3):
                for m in range(2,i-l-n-1):
                    s=i-m-n-l
                    if m<=n and n<=s: #Avoid duplicate conditions
                        for Rm in R[m]:
                            lowlim=(m<n and [0] or [R[m].index(Rm)])[0]
                            for Rn in R[n][lowlim:]:
                                lowlim2=(n<s and [0] or [R[n].index(Rn)])[0]
                                for Rs in R[s][lowlim2:]:
                                    ps=_powerString("T",l,powchar="^")
                                    W[i].append(RootedTree("{"+ps+Rm+Rn+Rs+"}"))
        for l in range(0,i-7): #level 4
            for n in range(2,i-l-5):
                for m in range(2,i-l-n-3):
                    for s in range(2,i-l-n-m-1):
                        t=i-s-m-n-l
                        if s<=t and n<=s and m<=n: #Avoid duplicate conditions
                            for Rm in R[m]:
                                lowlim=(m<n and [0] or [R[m].index(Rm)])[0]
                                for Rn in R[n][lowlim:]:
                                    lowlim2=(n<s and [0] or [R[n].index(Rn)])[0]
                                    for Rs in R[s][lowlim2:]:
                                        lowlim3=(s<t and [0] or [R[s].index(Rs)])[0]
                                        for Rt in R[t]:
                                            ps=_powerString("T",l,powchar="^")
                                            W[i].append(RootedTree("{"+ps+Rm+Rn+Rs+Rt+"}"))
    # The recursion above generates all trees except the 'blooms'
    # Now add the blooms:
    W[0].append(RootedTree("T"))
    for i in range(1,p):
        ps=_powerString("T",i,powchar="^")
        W[i].append(RootedTree("{"+ps+"}"))
  
    if ind=='all': return W[p-1]
    else: return W[p-1][ind]
    

def _powerString(s,npow,powchar="**",trailchar=''):
    r"""Raise string s to power npow with additional formatting."""
    if npow==0:
        return ""
    else:
        if npow==1:
            return s+trailchar
        else:
            return s+powchar+str(npow)+trailchar


#=====================================================
# Functions on trees
#=====================================================

def Dprod(tree,alpha):
    """
    Evaluate (alpha*D)(t).  Note that this is not equal to (D*alpha)(t).
    This function is necessary (rather than just using Gprod)
    in order to avoid infinite recursions.

    **Examples**::

        >>> from nodepy import rt
        >>> tree = rt.RootedTree('{T{T}}')
        >>> Dprod(tree,Emap)
        1/2
    """
    if tree == (0,): return 0
    if tree == (): return alpha(None)
    nleaves,subtrees=tree._parse_subtrees()
    result=alpha(RootedTree(()))**nleaves
    for subtree in subtrees:
        result*=alpha(subtree)
    return result

def Dprod_str(tree,alpha):
    if tree=='': return '0'
    if tree=='T': return alpha(RootedTree(''))
    nleaves,subtrees=tree._parse_subtrees()
    result=_powerString(alpha(RootedTree('T')),nleaves)
    for subtree in subtrees:
        if result!='': result+='*'
        result+=alpha(subtree)
    return result

def Dmap(tree):
    """ 
    Butcher's function D(t).  Represents differentiation.
    Defined by D(t)=0 except for D('T')=1.
    """
    return 1*(tree==())

def Dmap_str(tree):
    return str(int(tree=='T'))

def Gprod(tree,alpha,beta,alphaargs='',betaargs=[]):
    """ Returns the product of two functions on a given tree.
         See Butcher p. 276, Thm. 386A """
    return tree.Gprod(alpha,beta,alphaargs,betaargs)

def Gprod_str(tree,alpha,beta,alphaargs='',betaargs=[]):
    return tree.Gprod_str(alpha,beta,alphaargs,betaargs)

def Emap(tree,a=1):
    """ 
    Butcher's function E^a(t).
    Gives the B-series for the exact solution advanced 'a' steps
    in time.

    **Examples**::

        >>> from nodepy import rooted_trees as rt
        >>> tree=rt.RootedTree('{T^2{T{T}}}')
        >>> rt.Emap(tree)
        1/56
        >>> rt.Emap(tree,a=2)
        16/7

    **Reference**: 

        [butcher1997]_
    """
    return Rational(a**order(tree),(density(tree)))

def Emap_str(tree,a=1):
    return str(Rational(a**tree.order(),(tree.density())))


#=====================================================
def recursiveVectors(p,ind='all'):
#=====================================================
  """ 
    Generate recursive vectors using Albrecht's 'recursion 1'.
    These are essentially the order conditions for Runge-Kutta
    methods, excluding those that correspond to bushy trees.
    More specifically, these are the vectors that must be
    orthogonal to the vector of weights b.

    Note that the individual order conditions obtained from
    this algorithm are different from those obtained using Butcher's
    approach.  But as a set of conditions up to some order they
    are, of course, equivalent.

    Follows [albrecht1996]_ p. 1718

    .. warning::

        This code is complete only up to order 12.  We need to extend it 
        by adding more subloops for p>12.
  """
  if p>12: print 'recursiveVectors is not complete for orders p>12.'
  W=[[],[]]
  R=[[],[]]
  R.append(["tau[2]"])
  W.append(["tau[2]"])
  for i in range(3,p):
     #Construct R[i]
     R.append(["tau["+str(i)+"]"])
     for j in range(len(W[i-1])):
        R[i].append("A,"+W[i-1][j])
     #Construct W[i]
     #l=0:
     W.append(R[i][:])
     for l in range(1,i-1): #level 1
        ps=_powerString("C",l,trailchar=",")
        for j in range(len(R[i-l])):
          W[i].append(ps+R[i-l][j])
     for l in range(0,i-3): #level 2
        ps=_powerString("C",l,trailchar=",")
        for n in range(2,i-l-1):
          m=i-n-l
          if m<=n: #Avoid duplicate conditions
             for Rm in R[m]:
                lowlim=(m<n and [0] or [R[m].index(Rm)])[0]
                for Rn in R[n][lowlim:]:
                  W[i].append(ps+Rm+"*"+Rn)
     for l in range(0,i-5): #level 3
        ps=_powerString("C",l,trailchar=",")
        for n in range(2,i-l-3):
          for m in range(2,i-l-n-1):
             s=i-m-n-l
             if m<=n and n<=s: #Avoid duplicate conditions
                for Rm in R[m]:
                  lowlim=(m<n and [0] or [R[m].index(Rm)])[0]
                  for Rn in R[n][lowlim:]:
                     lowlim2=(n<s and [0] or [R[n].index(Rn)])[0]
                     for Rs in R[s][lowlim2:]:
                        W[i].append(ps+Rm+"*"+Rn+"*"+Rs)
     for l in range(0,i-7): #level 4
        ps=_powerString("C",l,trailchar=",")
        for n in range(2,i-l-5):
          for m in range(2,i-l-n-3):
             for s in range(2,i-l-n-m-1):
                t=i-s-m-n-l
                if s<=t and n<=s and m<=n: #Avoid duplicate conditions
                  for Rm in R[m]:
                     lowlim=(m<n and [0] or [R[m].index(Rm)])[0]
                     for Rn in R[n][lowlim:]:
                        lowlim2=(n<s and [0] or [R[n].index(Rn)])[0]
                        for Rs in R[s][lowlim2:]:
                          lowlim3=(s<t and [0] or [R[s].index(Rs)])[0]
                          for Rt in R[t]:
                             W[i].append(ps+Rm+"*"+Rn+"*"+Rs+"*"+Rt)
     for l in range(0,i-9): # level 5
        ps=_powerString("C",l,trailchar=",")
        for n in range(2,i-l-7):
          for m in range(2,i-l-n-5):
             for s in range(2,i-l-n-m-3):
                 for t in range(2,i-l-n-m-s-1):
                    u=i-t-s-m-n-l
                    if m<=n<=s<=t<=u: #Avoid duplicate conditions
                      for Rm in R[m]:
                         lowlim=(m<n and [0] or [R[m].index(Rm)])[0]
                         for Rn in R[n][lowlim:]:
                            lowlim2=(n<s and [0] or [R[n].index(Rn)])[0]
                            for Rs in R[s][lowlim2:]:
                              lowlim3=(s<t and [0] or [R[s].index(Rs)])[0]
                              for Rt in R[t]:
                                  lowlim4=(t<u and [0] or [R[t].index(Rt)])[0]
                                  for Ru in R[u]:
                                     W[i].append(ps+Rm+"*"+Rn+"*"+Rs+"*"+Rt+"*"+Ru)

  if ind=='all': return W[p-1]
  else: return W[p-1][ind]

def order(tree):
    """
    The order of a rooted tree, denoted $r(t)$, is the number of 
    vertices in the tree.

    **Examples**::

        >>> from nodepy import rooted_trees as rt
        >>> tree=rt.RootedTree( (((),()),()) )
        >>> rt.order(tree)
        5
    """
    if tree == (0,): return 0
    return 1 + sum([order(subtree) for subtree in tree])

def density(tree):
    r"""
    The density of a rooted tree, denoted by $\\gamma(t)$,
    is the product of the orders of the subtrees.

    **Examples**::

        >>> from nodepy import rooted_trees as rt
        >>> tree=rt.RootedTree('{T^2{T{T}}}')
        >>> tree = ((),(),((),((),)))
        >>> print tree
        {T^2{T{T}}}
        >>> rt.density(tree)
        56

    **Reference**: 

        - [butcher2003]_ p. 127, eq. 301(c)
    """
    gamma=order(tree)
    for subtree in tree:
        gamma *= density(subtree)
    return gamma

def symmetry(tree):
    r""" 
    The symmetry $\\sigma(t)$ of a rooted tree is...

    **Examples**::

        >>> from nodepy import rooted_trees as rt
        >>> tree=rt.RootedTree( ((),(),((),((),))) )
        >>> tree=rt.RootedTree('{T^2{T{T}}}')
        >>> tree.symmetry()
        2

    **Reference**: 

        - [butcher2003]_ p. 127, eq. 301(b)
    """
    sigma = 1
    tree = list(tree)
    while len(tree)>0:
        st=tree[0]
        nst=tree.count(st)
        sigma*=factorial(nst)*symmetry(st)**nst
        while st in tree: tree.remove(st)
    return sigma


def plot_tree(tree,nrows=1,ncols=1,iplot=1,ttitle=''):
    """
        Plots a rooted tree.

        *INPUT*: (optional)
            * nrows, ncols -- number of rows and columns of subplots
              in the figure
            * iplot        -- index of the subplot in which to plot
              this tree

        These are only necessary if plotting more than one tree
        in a single figure using subplot.

        *OUTPUT*: None.

        The plot is created recursively by
        plotting the root, parsing the subtrees, plotting the 
        subtrees' roots, and calling _plot_subtree on each child
    """
    import matplotlib.pyplot as plt

    if iplot==1: plt.clf()
    plt.subplot(nrows,ncols,iplot)
    plt.hold(True)
    plt.scatter([0],[0])
    if tree != (): _plot_subtree(tree,0,0,1.)

    fs=int(np.ceil(30./nrows))
    plt.title(ttitle,{'fontsize': fs})
    plt.hold(False)
    plt.axis('off')


def _plot_subtree(subtree,xroot,yroot,xwidth):
    """
        Recursively plots subtrees.  Should only be called from plot().

        INPUT:
            xroot, yroot -- coordinates at which root of this subtree 
                            is plotted
            xwidth -- width in which this subtree must fit, in order
                        to avoid possibly overlapping with others
    """
    import matplotlib.pyplot as plt
    ychild=yroot+1
    nchildren = len(subtree)

    dist=xwidth*(nchildren-1)/2.
    xchild=np.linspace(xroot-dist,xroot+dist,nchildren)
    plt.scatter(xchild,ychild*np.ones(nchildren))
    for i,subsubtree in enumerate(subtree):
        plt.plot([xroot,xchild[i]],[yroot,ychild],'-k')
        if subsubtree != ():
            _plot_subtree(subsubtree,xchild[i],ychild,xwidth/3.)


#=====================================================
#=====================================================
#DEPRECATED FUNCTIONS
#=====================================================
#=====================================================

def py2tex(codestr):
    """Convert a python code string to LaTex"""

    strout=codestr.replace("'","^T")
    strout=strout.replace("*","")
    strout=strout.replace(".^","^")
    strout='$'+strout+'$'
    return strout


if __name__ == "__main__":
    import doctest
    doctest.testmod()
