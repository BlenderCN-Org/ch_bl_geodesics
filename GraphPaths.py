import sys, time, math;
from mathutils import Vector;

import bpy;
from chenhan_pp.MeshTools import ensurelookuptable, getBMMesh;
from chenhan_pp.TrimeshCurvatures import need_curvatures;

try:
	import chenhancc;
	from chenhancc import CRichModel as RichModel, CICHWithFurtherPriorityQueue, CPoint3D, CFace;
except ImportError:
	from chenhan_pp.CICHWithFurtherPriorityQueue import CICHWithFurtherPriorityQueue
# from chenhan.geodesics import CICHWithFurtherPriorityQueue;


import numpy as np;
from mathutils import Vector, Color;
import matplotlib.cm as cm;
from matplotlib.cm import get_cmap;
import matplotlib.colors as clrs;


def isFastAlgorithmLoaded():
	try:
		import chenhancc;
		return True;
	except (NameError):
		return False;



def rgb(minimum, maximum, value):
	minimum, maximum = float(minimum), float(maximum)
	ratio = 2 * (value-minimum) / (maximum - minimum)
	b = int(max(0, 255*(1 - ratio)))
	r = int(max(0, 255*(ratio - 1)))
	g = 255 - b - r
	return r, g, b



def applyColoringForMeshErrors(context, error_mesh, error_values, *, A = None, B = None, v_group_name = "lap_errors", normalize = False):
        
        
        print(error_values[:50]);
        c = error_values.T;
        
        if(not A and not B):
            B = np.amax(c);
            A = np.amin(c);
        
        norm = clrs.Normalize(vmin=A, vmax=B);
#         cmap = cm.jet;
        cmap = get_cmap("jet");
#         cmap = clrs.LinearSegmentedColormap.from_list(name="custom", colors=all_colors);
        m = cm.ScalarMappable(norm=norm, cmap=cmap);
        final_colors = m.to_rgba(c);
        final_weights = norm(c);
        
        colors = {};
        L_error_color_values = {};
        
        for v in error_mesh.data.vertices:
        	(r,g,b,a) = final_colors[v.index];
        	#color = Color((rgb(A, B, error_values[v.index])));
        	color = Color((r, g, b));
        	L_error_color_values[v.index] = color;
        	colors[v.index] = final_weights[v.index];
        
        if(None == error_mesh.vertex_groups.get(v_group_name)):
            error_mesh.vertex_groups.new(name=v_group_name);
        
        if(None == error_mesh.data.vertex_colors.get(v_group_name)):
            error_mesh.data.vertex_colors.new(v_group_name);
            
        group_ind = error_mesh.vertex_groups[v_group_name].index;
        lap_error_colors = error_mesh.data.vertex_colors[v_group_name];
        
        bm = getBMMesh(context, error_mesh, False);
        ensurelookuptable(bm);
        
        for v in error_mesh.data.vertices:
            n = v.index;
            error_mesh.vertex_groups[group_ind].add([n], colors[v.index], 'REPLACE');
            
            b_vert = bm.verts[v.index];
            
            for l in b_vert.link_loops:
                lap_error_colors.data[l.index].color = L_error_color_values[v.index];
            
        bm.free();
        
        try:
#             material = bpy.data.materials[error_mesh.name+'_'+v_group_name+'ErrorsMaterial'];
            material = bpy.data.materials[error_mesh.name+'_'+v_group_name];
        except:
#             material = bpy.data.materials.new(error_mesh.name+'_'+v_group_name+'ErrorsMaterial');
            material = bpy.data.materials.new(error_mesh.name+'_'+v_group_name);
            error_mesh.data.materials.append(material);
            
        material.use_vertex_color_paint = True;   


class GraphPaths:
    #Reference to the blender object;
    m_mesh = None;
    #Reference to the bm_data;
    m_bmesh = None;
    #Reference to the blender context;
    m_context = None;
    #indices of seed paths;
    m_seed_indices = None;
    
    def __init__(self, context, mesh, bm_mesh):
        self.m_mesh = mesh;
        self.m_bmesh = bm_mesh;
        self.m_context = context;
        self.m_seed_indices = [];
    
    
    def removeSeedIndex(self, seed_index):
        try:
            index = self.m_seed_indices.index(seed_index);
            self.m_seed_indices.remove(seed_index);
            return index;
        except ValueError:
            return -1;
    
    def addSeedIndex(self, seed_index, passive=False):
        try:
            self.m_seed_indices.index(seed_index);
        except ValueError:
            self.m_seed_indices.append(seed_index);
    
    def path_between(self, seed_index, target_index):        
        return [];
    
    def getSeedIndices(self):
        return self.m_seed_indices;


class ChenhanGeodesics(GraphPaths):
    
    m_all_geos = None;
    m_richmodel = None;
    algo = None;
    
    def __init__(self, context, mesh, bm_mesh, richmodel):
        super().__init__(context, mesh, bm_mesh);
        self.m_all_geos = [];
        print('DO YOU HAVE THE FAST VERSION ? ', isFastAlgorithmLoaded());
        if(isFastAlgorithmLoaded()):
        	verts = [];
        	faces = [];
        	loops = mesh.data.loops;
        	self.m_richmodel = RichModel();
        	for v in mesh.data.vertices:
        		p3d = CPoint3D(v.co.x, v.co.y, v.co.z);
        		verts.append(p3d);
        	for f in mesh.data.polygons:
        		f_vids = [loops[lid].vertex_index for lid in f.loop_indices];
        		faces.append(CFace(f_vids[0], f_vids[1], f_vids[2]));
        		
        	self.m_richmodel.LoadModel(verts, faces);
        	self.m_richmodel.Preprocess();
        else:
        	self.m_richmodel = richmodel;
        
        ensurelookuptable(bm_mesh);
#         self.algo = CICHWithFurtherPriorityQueue(inputModel=self.m_richmodel, indexOfSourceVerts=[v.index for v in bm_mesh.verts]);
#         self.algo.Execute();
#         self.algo.PickShortestPaths(self.m_richmodel.GetNumOfVerts());
#         print('TABLE OF RESULTING PATHS ::: ');
#         print(self.algo.m_tableOfResultingPaths[0], self.m_richmodel.Vert(0));
    def getRichModel(self):
    	return self.m_richmodel;
    
    def addSeedIndex(self, seed_index, passive=False):
        super().addSeedIndex(seed_index);
        index = self.m_seed_indices.index(seed_index);
        if(not passive):
            try:
                geos_index = self.m_all_geos[index];
            except IndexError:
                alg = None;
                start = time.time();
                if(isFastAlgorithmLoaded()):
                	alg = CICHWithFurtherPriorityQueue(self.m_richmodel, set([seed_index]));
                else:
                	alg = CICHWithFurtherPriorityQueue(inputModel=self.m_richmodel, indexOfSourceVerts=[seed_index]);
                alg.Execute();
                end = time.time();
                print('TOTAL TIME FOR SEEDING ::: ', (end - start)," seconds");
                self.m_all_geos.append(alg);
#                 self.m_all_geos.append(self.algo);
        else:
            self.m_all_geos.append(None);
    
    def removeSeedIndex(self, seed_index):
        removed_index = super().removeSeedIndex(seed_index);
        if(removed_index != -1):
            del self.m_all_geos[removed_index];
            
    def path_between(self, seed_index, target_index):        
        try:
            indice = self.m_seed_indices.index(seed_index);
            
            if(not self.m_all_geos[indice]):
                if(isFastAlgorithmLoaded()):
                	alg = CICHWithFurtherPriorityQueue(self.m_richmodel, set([seed_index]));
                else:
                 	alg = CICHWithFurtherPriorityQueue(inputModel=self.m_richmodel, indexOfSourceVerts=[seed_index]);
                alg.Execute();
#                 self.m_all_geos[indice] = alg;
#                 ensurelookuptable(self.m_bmesh);
#                 self.algo = CICHWithFurtherPriorityQueue(inputModel=self.m_richmodel, indexOfSourceVerts=[v.index for v in self.m_bmesh.verts]);
#                 self.algo.Execute();
#                 self.m_all_geos[indice] = self.algo;
            
            if(isFastAlgorithmLoaded()):
            	pathp3d = self.m_all_geos[indice].FindSourceVertex(target_index,[]);
            else:
            	pathp3d, sourceindex = self.m_all_geos[indice].FindSourceVertex(target_index);
            path = [];
#             print('SOURCE INDEX ::: ', sourceindex, ' GIVEN SEED INDEX ::: ', seed_index, ' GIVEN TARGET INDEX ', target_index);
#             print('TABLE OF RESULTING PATHS ::: ');
#             print(self.algo.m_tableOfResultingPaths);
            
            
            for eitem in pathp3d:
            	vco = eitem.Get3DPoint(self.m_richmodel);
            	if(isFastAlgorithmLoaded()):
            		vco = Vector((vco.x, vco.y, vco.z));
            	path.append(self.m_mesh.matrix_world *  vco);
            
            return path;
        
        except ValueError:
            print("THE intended seed_index does not exist, so returning NONE");
            return None;
        
class AnisotropicGeodesics(ChenhanGeodesics):
    user_gamma = 0.1;    
    
    def __init__(self, context, mesh, bm_mesh, richmodel):
        super().__init__(context, mesh, bm_mesh, richmodel);
        ensurelookuptable(bm_mesh);
        self.makeMeshUsingCurvatures();
        
    def makeMeshUsingCurvatures(self):
    	k1_l, k2_l, sx, p1_l, p2_l, mean, gauss_l = need_curvatures(self.m_bmesh, self.m_mesh);
    	k1_l = np.abs(k1_l);
    	k2_l = np.abs(k2_l);
    	applyColoringForMeshErrors(self.m_context, self.m_mesh, sx, v_group_name = "sx_colors");
#     	for edge in self.m_richmodel.m_Edges:
#     		left_vert_index = edge.indexOfLeftVert;
#     		right_vert_index = edge.indexOfRightVert;
#     		p3d_left = self.m_richmodel.m_Verts[left_vert_index];
#     		p3d_right = self.m_richmodel.m_Verts[right_vert_index];
#     		left_vert = Vector((p3d_left.x, p3d_left.y, p3d_left.z));
#     		right_vert = Vector((p3d_right.x, p3d_right.y, p3d_right.z));
#     		v = right_vert - left_vert;
#     		k1, k2, u1, u2 = k1_l[left_vert_index], k2_l[left_vert_index], p1_l[left_vert_index], p2_l[left_vert_index];
#     		s_x = abs(k1) - abs(k2);
#     		lambda_1 = 1.0 + (self.user_gamma * s_x);
#     		lambda_2 = 1.0 / (1.0 + (self.user_gamma * s_x));
#     		theta = v.angle(u1);
# #     		print(edge.indexOfLeftVert, edge.indexOfRightVert, theta, lambda_1, lambda_2);
# #     		gx_v = edge.length * (((lambda_1 * math.cos(theta))**2) + ((lambda_2 * math.sin(theta))**2))**0.5;
#     		gx_v = 1.0 * (((lambda_1 * math.cos(theta))**2) + ((lambda_2 * math.sin(theta))**2))**0.5;
#     		if isinstance(gx_v, complex):
#     			gx_v = gx_v.real;
#     		edge.length = gx_v;



