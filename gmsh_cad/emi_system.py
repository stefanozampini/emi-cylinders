from dolfin import *
from tiling import as_meshf

parameters['form_compiler']['representation'] = 'uflacs'
parameters['form_compiler']['cpp_optimize'] = True
parameters['form_compiler']['cpp_optimize_flags'] = '-O3 -ffast-math -march=native'
parameters['ghost_mode'] = 'shared_facet'

mesh_file = 'tile_2x2.h5'
container_type = 'mf'

comm = mpi_comm_world()
h5 = HDF5File(comm, mesh_file, 'r')
mesh = Mesh()
h5.read(mesh, 'mesh', False)
# The mesh comes in micro meters. Below it is more convenient to work in cm
mesh.coordinates()[:] *= 1E-4

# Facets in the mesh have tags 0, 1, 2. One is for interfaces between
# cells and cells and the exterior. Two is used for marking boundary facets
# of the domain - this is where typically zero DirichletBCs are applied
# for the potential. The domain is split into 2 subdomains marked as 1 
# and 2 (cell interior, cell exterior). These differ by conductivities

iface_tag, cell_tag = 1, 1
bdry_tag, ext_tag = 2, 2

surfaces = MeshFunction('size_t', mesh, mesh.topology().dim()-1, 0)
h5.read(surfaces, 'surfaces')

volumes = MeshFunction('size_t', mesh, mesh.topology().dim(), 0)
h5.read(volumes, 'volumes')

cell = mesh.ufl_cell()
# We have 3 spaces S for sigma = -kappa*grad(u)   [~electric field]
#                  U for potential u
#                  Q for transmebrane potential p
Sel = FiniteElement('RT', cell, 1)
Vel = FiniteElement('DG', cell, 0)
Qel = FiniteElement('Discontinuous Lagrange Trace', cell, 0)

W = FunctionSpace(mesh, MixedElement([Sel, Vel, Qel]))
sigma, u, p = TrialFunctions(W)
tau, v, q = TestFunctions(W)

# W.sub(0) bcs set strongly correspond to insulation. Skipping (tau.n)*u on 
# bdry means potential there is weakly zero, grounding.

# Make measures aware of subdomains
dx = Measure('dx', domain=mesh, subdomain_data=volumes)
dS = Measure('dS', domain=mesh, subdomain_data=surfaces)
ds = Measure('ds', domain=mesh, subdomain_data=surfaces)
    
# Normal fo the INTERIOR surface. Note that 1, 2 marking of volume makes
# 2 cells the '+' cells w.r.t to surface and n('+') would therefore be their
# outer normal (that is an outer normal of the outside). ('-') makes the orientation
# right (set later)
n = FacetNormal(mesh)

# Now onto the weak form
# Electric properties of membrane and interior/exterior
C_m = Constant(1)         # 1 mu F / cm^2                        
cond_int = Constant(5)    # 5 mS / cm
cond_ext = Constant(20)   # 20 mS / cm
# Time step
dt_fem = Constant(1E-3)   # ms

# The source term as a function Q is coming from ODE solver. Here it is
# just some random function
Q = FunctionSpace(mesh, Qel)  
p0 = interpolate(Constant(1), Q)
# And additional source on the boundary is the ionic current. For simplicity
I_ion = p0

# The system
a = ((1/cond_int)*inner(sigma, tau)*dx(cell_tag)+(1/cond_ext)*inner(sigma, tau)*dx(ext_tag)
     - inner(div(tau), u)*dx(cell_tag) - inner(div(tau), u)*dx(ext_tag)
     + inner(p('+'), dot(tau('+'), n('-')))*dS(iface_tag)
     - inner(div(sigma), v)*dx(cell_tag) - inner(div(sigma), v)*dx(ext_tag)
     + inner(q('+'), dot(sigma('+'), n('-')))*dS(iface_tag)
     - (C_m/dt_fem)*inner(q('+'), p('+'))*dS(iface_tag))

L = inner(q('+'), I_ion('+')-(C_m/dt_fem)*p0('+'))*dS(iface_tag)

# NOTE: in general the cell interfaces might end up on the surface boundary
a += (inner(p, dot(tau, n))*ds(iface_tag)
      + inner(q, dot(sigma, n))*ds(iface_tag)
      - (C_m/dt_fem)*inner(q, p)*ds(iface_tag))

L += inner(q, I_ion-(C_m/dt_fem)*p0)*ds(iface_tag)

# Additional terms to set to zero the dofs of W.sub(2) which are not on
# the interfaces
a -= inner(p('+'), q('+'))*dS(0) + inner(p, q)*ds(bdry_tag)
L -= inner(Constant(0)('+'), q('+'))*dS(0) + inner(Constant(0), q)*ds(bdry_tag)

A, b = PETScMatrix(), PETScVector()
assemble_system(a, L, A_tensor=A, b_tensor=b)

# dms = [set(W.sub(i).dofmap().dofs()) for i in range(3)]
# for i, dmi in enumerate(dms):
#     for dmj in dms[i+1:]:
#         print dmi & dmj

# import numpy as np
# for i in range(A.size(0)):
#     cols, vals = A.getrow(i)
#     if np.linalg.norm(vals, 1) == 0:
#         print (i, vals), [(i in dm) for dm in dms]
# print A.size(0), A.norm('linf')

# print np.sort(np.abs(np.linalg.eigvals(A.array())))[0:20]

f = Expression(('sin(pi*(x[0]))', 'sin(pi*(x[1]))', 'sin(pi*(x[2]))',
                'sin(pi*(x[0]+x[1]+x[2]))',
                'sin(pi*(x[0]))'), degree=1)

g = Expression(('cos(pi*(x[0]))', 'sin(pi*(x[1]))', 'cos(pi*(x[2]))',
                'sin(pi*(x[0]+x[1]+x[2]))',
                'cos(pi*(x[0]))'), degree=1)


x = interpolate(f, W).vector()
as_backend_type(x).update_ghost_values()

y = interpolate(g, W).vector()
as_backend_type(y).update_ghost_values()

A.mult(x, b)
as_backend_type(b).update_ghost_values()

info("%g %g" %  (b.inner(y), b.norm('l2')))
