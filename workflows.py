import nipype.interfaces.fsl as fsl
import nipype.interfaces.mrtrix as mrt
import nipype.interfaces.freesurfer as fs
import nipype.interfaces.utility as niu
import nipype.pipeline.engine as pe
from nipype.workflows.dmri.fsl.artifacts import ecc_pipeline 
import utility as su 

def ReconAll():
    pass


def Surface(name='surface'):
    """ Surface workflow
    Generate vertices.txt, triangles.txt and region_mapping.txt
    """

    inputnode = pe.Node(interface=niu.IdentityInterface(fields=['pials', 'annots', 'ref_tables']), name='inputnode')
    inputnode.iterables = [('pials', ["/Users/timp/Work/data/af/surf/rh.pial",
                             "/Users/timp/Work/data/af//surf/lh.pial"]),
                           ('annots', ["/Users/timp/Work/data/af/label/rh.aparc.annot",
                              "/Users/timp/Work/data/af/label/lh.aparc.annot"]),
                            ('ref_tables', ["/Users/timp/Desktop/scripts/rh_ref_table.txt",
                                   "/Users/timp/Desktop/scripts/lh_ref_table.txt"])]
    inputnode.synchronize = True

    pial2asc = pe.Node(interface=su.MRIsConvert(), name='pial2asc')
    pial2asc.inputs.out_datatype ='asc'
    extract_high = pe.Node(interface=su.Fs2Txt(), name='extract_high')
    txt2off = pe.Node(interface=su.Txt2Off(), name='txt2off')
    remesher = pe.Node(interface=su.Remesher(), name='remesher')
    off2txt = pe.Node(interface=su.Off2Txt(), name='off2txt')
    region_mapping = pe.Node(interface=su.RegionMapping(), name='region_mapping', 
                                iterfield=['aparc_annot', 'ref_table', 'vertices_downsampled',
                                'triangles_downsampled', 'vertices'])
    correct_region_mapping = pe.Node(interface=su.CorrectRegionMapping(), name='correct_region_mapping')
    check_region_mapping = pe.Node(interface=su.CheckRegionMapping(), name='check_region_mapping',
                                      iterfield=['vertices', 'triangles', 'region_mapping'])
    reunify_both_hemi = pe.JoinNode(interface=su.ReunifyBothHemisphere(), joinsource="inputnode",
                                    joinfield=['vertices', 'triangles', 'textures'], name='reunify_both_hemi')


    wf = pe.Workflow(name='workflow_surface')
    wf.connect([
        (inputnode, pial2asc,[('pials','in_file')]),
        (inputnode, region_mapping, [('annots', 'aparc_annot'),
                       ('ref_tables','ref_table')]),
        (pial2asc, extract_high, [('converted','surface')]),
        (extract_high, txt2off, [('vertices','vertices'),
                                 ('triangles','triangles')]),
        (extract_high, region_mapping,[('vertices','vertices')]),
        (txt2off, remesher, [('surface_off','in_file')]),
        (remesher, off2txt, [('out_file','surface_off')]),
        # work to do on region mapping
        (off2txt, region_mapping, [('vertices_txt','vertices_downsampled'),
                                   ('triangles_txt','triangles_downsampled')]),
        (off2txt, correct_region_mapping, [('vertices_txt','vertices'),
                                           ('triangles_txt','triangles')]),
        (off2txt, check_region_mapping, [('vertices_txt','vertices'),
                                         ('triangles_txt','triangles')]),
        (off2txt, reunify_both_hemi, [('vertices_txt','vertices'),
                                         ('triangles_txt','triangles')]),
        (region_mapping, correct_region_mapping,[('out_file','texture')]),
        (correct_region_mapping, check_region_mapping, [('texture_corrected','region_mapping')]),
        (check_region_mapping, reunify_both_hemi, [('region_mapping', 'textures')]),
        ])

    return wf


def SubcorticalSurface(name="subcorticalsurfaces"):
    """ extraction of the subcortical surfaces from FreeSurfer"""
    inputnode = pe.Node(interface=niu.IdentityInterface(fields=['in_subject_id']), name='inputnode')
    aseg2srf = pe.Node(interface=su.Aseg2Srf(), name='aseg2srf')
    list_subcortical = pe.MapNode(interface=su.ListSubcortical(), name=list_subcortical, iterfield=['in_file'])
    outputnode = pe.MapNode(interface=niu.IdentityInterface(fields=['out_fields']), name='outputnode')

    wf = pe.Workflow(name=name)
    wf.connect([
        (inputnode, aseg2srf, [('in_subject_id', 'in_subject_id')]),
        (aseg2srf, list_subcortical, [('out_files', 'in_file')]),
        (list_subcortical, outputnode, [('out_files', 'in_file')])])

    return wf

def Connectivity(name="connectivity"):
    inputnode = pe.Node(interface=niu.IdentityInterface(fields=['in_file']), name='inputnode')
    convert_dicom2nii = pe.Node(interface=mrt.MRConvert(), name='convert_dicom2nii')
    extract_bvecs_bvals = pe.Node(interface=mtr3.utils.MRInfo(), name='extract_bvecs_bvals')
# ecc = ecc_pipeline()
    convert_nii2dwi = pe.Node(interface=mrt.MRConvert(), name='convert_nii2dwi')
    create_mask = pe.Node(interface=mrt3.Dwi2Mask(), name='create_mask')
    dwi_extract_lowb = pe.Node(interface=mrt3.DwiExtract(), name='dwi_extract_lowb')
    lowb_mif2lowb_nii = pe.Node(interface=mrt.MRConvert(), name='lowb_mif2lowb_nii')
    cor = Coregistration()
    dwi2response = pe.Node(interface=mrt3.preprocess().Dwi2Response, name='dwi2response')
    dwi2fod = pe.Node(interface=mrt3.preprocess().Dwi2Fod, name='dwi2fod')
    dwi2fod.inputs.lmax = 8
    act_anat_prepare_fsl = pe.node(interface=mrt3.ActAnatPrepareFSL(), name='act_anat_prepare_fsl')
    fivett2gmwmi = pe.Node(interface=mrt3.fivett2Gmwmi(), name='5tt2gmwmi')
    tckgen = pe.node(interface=mrt3.tracking.Tckgen(), name='tckgen')
    tckgen.inputs.unidirectional = True
    tckgen.inputs.seed_gmwmi = 'iFOD2'
    tckgen.inputs.maxlength = 150
    tckgen.inputs.num = 5000000
    tcksift = pe.Node(interface=mrt3.TckSift(), neame='tcksift')
    tcksift.inputs.term_number = 2500000
    labelconfig = pe.Node(interface=mrt3.utils.LabelConfig(), name='labelconfig')
    tck2connectome_weights = pe.Node(interface=mrt3.tracking.Tck2Connectome(), name='tck2connectome_weights')
    tck2connectome_weights.inputs.assignement_radial_search = 2
    tck2connectome_tract_lengths = pe.Node(interface=mrt3.tracking.Tck2Connectome(), name='tck2connectome_tract_lengths')
    tck2connectome_tract_lengths.inputs.assignement_radial_search = 2
    tck2connectome_tract_lengths.inputs.zero_diagonal = True
    tck2connectome_tract_lengths.inputs.metric = 'meanlength'
    compute_connectivity = pe.Node(interface=su.ComputeConnectivityFiles(), name='compute_connecitivty')
    outputnode = pe.Node(interface=nit.IdentityInterface(fields=(['out_weights', 'out_tract_lengths']), name='outputnode'))

    wf = pe.Workflow(name=name)
    wf.connect([
        (inputnode, convert_dicom2nii, [('in_file', 'in_file')]),
        (convert_dicom2nii, extract_bvecs_bvals, [('converted', 'in_files')]),
        (convert_dicom2nii, convert_nii2dwi, [('converted', 'in_file'),
                                              ('bvecs', 'bvals', 'fslgrad')]),
        (convert_nii2dwi, create_mask, [('converted', 'in_file')]),
        (convert_nii2dwi, dwi_extract_lowb, [('converted', 'in_file')]),
        (create_mask, dwi_extract_lowb, [('out_file', 'in_file')]),
        (dwi_extract_lowb, lowb_mif2lowb_nii, [('out_file', 'in_file')]),
        (inputnode, cor, [('in_T1.mgz', 'in_T1.mgz')]),
        (inputnode, cor, [('in_aparcaseg.mgz', 'in_aparcaseg.mgz')]),
        (lowb_mif2lowb_nii, cor, [('out_file', 'in_aparcaseg.mgz')]),
        (convert_nii2dwi, dwi2response, [('out_file', 'dwi')]),
        (create_mask, dwi2response, [('out_file', 'mask')]),
        (convert_nii2dwi, dwi2fod, [('out_file', 'dwi')]),
        (dwi2response, dwi2fod, [('response', 'response')]),
        (create_mask, dwi2fod, [('out_file', 'mask')]),
        (cor, act_anat_prepare_fsl, [('out_T1_diff', 'in_file')]),
        (act_anat_prepare_fsl, fivett2gmwmi, [('out_file', 'in_file')]),
        (dwi2fod, tckgen, [('sh_out_file', 'source')]),
        (fivett2gmwmi, tckgen, [('out_file', 'seed_gmwmi')]),
        (tckgen, tcksift, [('tracks', 'tracks')]),
        (dwi2fod, tcksift, [('sh_out_file', 'source')]),
        (cor, labelconfig, [('out_aparcaseg_diff', 'labels_in')]),
        (inputnode, labelconfig, [('fs_region.txt', 'config')]),
        (inputnode, labelconfig, [('FreeSurferColorLUT.txt', 'lut_freesurfer')]),
        (tcksift, tck2connectome_weights, [('out_file', 'tracks_in')]), 
        (labelconfig, tck2connectome_weights, [('labels_out', 'nodes_in')]),
        (tcksift, tck2connectome_tract_lengths, [('out_file', 'tracks_in')]), 
        (labelconfig, tck2connectome_tract_lengths, [('labels_out', 'nodes_in')]),
        (tck2connectome_weights, compute_connectivity, [('connectome_out', 'in_file')]),
        (tck2connectome_tract_lengths, compute_connectivity, [('connectome_out', 'in_file')]),
        (compute_connectivity, output_node, [('weights.txt', 'out_weights.txt'),
                                             ('tract_lengths.txt', 'out_tract_lengths.txt')])
        ])


    return wf


        
        


def Coregistration(name='coregistration'):
    inputnode = pe.Node(niu.IdentityInterface(fields=['in_T1.mgz', 'in_lowb.nii',
                        'in_aparcaseg.mgz']), name='inputnode')
    T1_mgz2nii = pe.Node(interface=fs.preprocess.MRIConvert(), name='T1_mgz2nii')
    T1_mgz2nii.inputs.in_type = 'mgz'
    T1_mgz2nii.inputs.out_type = 'nii'
    T1_mgz2nii.inputs.out_orientation = 'RAS'
    aparcaseg_mgz2nii = pe.Node(interface=fs.preprocess.MRIConvert(), name='aparcaseg_mgz2nii')
    aparcaseg_mgz2nii.inputs.in_type = 'mgz'
    aparcaseg_mgz2nii.inputs.out_type = 'nii'
    aparcaseg_mgz2nii.inputs.out_orientation = 'RAS'
    reorient2std = pe.Node(interface=fsl.utils.Reorient2Std(), name='reorient2std')
    diff2struct = pe.Node(interface=fsl.preprocess.FLIRT(), name='diff2struct')
    diff2struct.inputs.searchr_x = [180, 180]
    diff2struct.inputs.searchr_y = [180, 180]
    diff2struct.inputs.searchr_z = [180, 180]
    diff2struct.inputs.cost = 'mutualinfo'
    convertxfm = pe.Node(interface=fsl.utils.ConvertXFM(), name='convertXFM')
    convertxfm.inputs.invert_xfm = True
    aparcaseg2diff = pe.Node(interface=fsl.preprocess.ApplyXFM(), name='aparcaseg2diff')
    aparcaseg2diff.inputs.apply_xfm = True
    aparcaseg2diff.inputs.interp = 'nearestneighbour'
    T12diff = pe.Node(interface=fsl.preprocess.ApplyXFM(), name='T12diff')
    T12diff.inputs.apply_xfm = True
    T12diff.inputs.interp = 'nearestneighbour'
    outputnode = pe.Node(niu.IdentityInterface(fields=['out_aparcaseg_diff', 'out_T1_diff'], name='outputnode'))
    
    wf = pe.Workflow(name=name)
    wf.connect([
        (inputnode, T1_mgz2nii, [('in_T1.mgz', 'in_file')]),
        (inputnode, aparcaseg_mgz2nii, [('in_aparcaseg.mgz', 'in_file')]),
        (aparcaseg_mgz2nii, reorient2std, [('out_file', 'in_file')]),
        (inputnode, diff2struct, [('in_lowb.nii', 'in_file')]),
        (T1_mgz2nii, diff2struct, [('out_file', 'reference')]),
        (diff2struct, convertxfm, [('out_matrix_file', 'in_file')]),
        (aparcaseg_mgz2nii, aparcaseg2diff, [('out_file', 'in_file')]),
        (inputnode, aparcaseg2diff, [('in_lowb.nii', 'reference')]),
        (convertxfm, aparcaseg2diff, [('out_file', 'in_matrix_file')]),
        (T1_mgz2nii, T12diff, [('out_file', 'in_file')]),
        (inputnode, T12diff, [('in_lowb.nii', 'reference')]),
        (convertxfm, T12diff, [('out_file', 'in_matrix_file')]),
        ])

    return wf







