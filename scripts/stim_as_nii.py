#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jul 28 10:51:30 2021

@author: dlinhardt
"""
import numpy as np
from os import path, makedirs
import nibabel as nib
from scipy.io import loadmat
from scipy.ndimage import shift
from glob import glob
import sys

# convert stimulus from matlab to .nii.gz if not done yet
def stim_as_nii(sub, sess, bidsDir, outP, etcorr, forceParams, use_numImages, force, verbose):
    '''
    Here the stimuli as shown to the subject will be saved as binarised version
    into nifti files for the analysis. We find the stimuli in the _params.mat 
    files. Per stimulus only one file will be saved.
    If we wanna do eyetracker correction we read the _gaze.mat file and shift
    the stimulus in the opposite direction as the subject was looking. This 
    will allow for a better model creation during the analysis when we had 
    gaze instabilities. This will need for stimulus files specific for
    sub,ses,task,run!
    '''
    
    def die(*args):
        print(*args)
        sys.exit(1)
    def note(*args):
        if verbose: print(*args)
        return None
   
    if forceParams==['']:forceParams=False
    if forceParams:
        paramsFile, task = forceParams
        logPs = [path.join(bidsDir, 'sourcedata', 'vistadisplog', paramsFile)]
    else:  
        logPs = np.array(glob(path.join(bidsDir, 'sourcedata', 'vistadisplog', 
                                        f'sub-{sub}', '*', '*1_params.mat')))
    
    # check if we found params files
    if len(logPs)==0:
        print('We could not find the vistadisp output files in bids format at:')
        print(path.join(bidsDir, 'sourcedata', 'vistadisplog', 
                                    f'sub-{sub}', 'ses-XXX'))
        print('alternatively use config "force_params_file":"[<file>,<task>]"')
        die('Therefore we will break here!')
        
    # go through all param files and creat stimuli from them
    for logP in logPs:
        stim  = loadmat(logP, simplify_cells=True)['params']['loadMatrix'].split('/')[-1].split('\\')[-1]
        stimP = path.join(bidsDir, 'sourcedata', 'stimuli', stim)
        

        if not forceParams:
            task = logP.split('task-')[-1].split('_run')[0]
        

        # create output dirs
        makedirs(path.join(outP, 'stimuli'), exist_ok=True)
        oFname = path.join(outP, 'stimuli', f'task-{task}_apertures.nii.gz')

        note(f'[stim_as_nii.py] Now working with params: {logP} and images file {stimP}, task is {task}, output file will be {oFname}') 
        
        if not path.isfile(oFname) or force:
            if not path.isfile(stimP): 
                exit(f'Did not find stim File: {stimP}')
            
            # loat the mat files defining the stimulus
            imagesFile = loadmat(stimP, simplify_cells=True)
            paramsFile = loadmat(logP, simplify_cells=True)
            
            # get all values necessary
            seq       = paramsFile['stimulus']['seq']
            tr        = paramsFile['params']['tr']
            prescan   = paramsFile['params']['prescanDuration']
            # There are projects with 'images' directly or 'stimulus.images', check both
            fields    = imagesFile.keys()
            if 'stimulus' in fields: images = imagesFile['stimulus']['images']
            elif 'images' in fields: images = imagesFile['images']
            else: die('Neither stimulus or images fields found on image file')

            note(f'Read params: seq.shape {seq.shape}, tr: {tr}, prescan: {prescan}, images.shape: {images.shape}')

            # build and binarise the stimulus
            stimImagesU, stimImagesUC = np.unique(images, return_counts=True)
            images[images!=stimImagesU[np.argmax(stimImagesUC)]] = 1
            images[images==stimImagesU[np.argmax(stimImagesUC)]] = 0
            
            # create it from frames
            if use_numImages:
                # load in the numImages
                numImages = paramsFile['params']['numImages']
                idx = np.linspace(0, len(seq)-1, int(numImages+prescan/tr), dtype=int)
            else:
                print('Using seqtiming')
                # calculate the numImages from seqTiming
                seqTiming = paramsFile['stimulus']['seqtiming']
                numImages = len(seq) * seqTiming[1] / tr
                idx = np.linspace(0, len(seq)-1, int(numImages), dtype=int)
                    
            oStimVid = images[:,:, seq[idx]-1]     
            note(f'Using params.numImages= {numImages}, idx.shape: {idx.shape}, oStimVid.shape: {oStimVid.shape}')
            
            # remove prescanDuration from stimulus
            if prescan > 0:
                oStimVid = oStimVid[:,:, int(prescan/tr):]
                note(f'Prescan = {prescan}, removing volumes at the beginning, now oStimVid.shape: {oStimVid.shape}')
    
            # save the stimulus as nifti
            img = nib.Nifti1Image(oStimVid[:,:,None,:].astype('float64'), np.eye(4))
            img.header['pixdim'][1:5] = [1,1,1,tr]
            img.header['qoffset_x']=img.header['qoffset_y']=img.header['qoffset_z'] = 1
            img.header['cal_max'] = 1
            img.header['xyzt_units'] = 10
            nib.save(img, oFname)
            note(f'saving file in {oFname}')
    
    #%% do the shifting for ET corr
    if etcorr and not forceParams:    
        note('etcorr is true and it will do it now')
        # base paths
        outPET = outP.replace('/sub-', '_ET/sub-')
        
        # create the output folders
        makedirs(outPET, exist_ok=True)
                
        for sesI,ses in enumerate(sess):
            
            logPs = np.array(glob(path.join(bidsDir, 'sourcedata', 'vistadisplog', 
                                            f'sub-{sub}', f'ses-{ses}', '*_params.mat')))
            
            for logP in logPs:
                stim  = loadmat(logP, simplify_cells=True)['LoadStimName']
                stimP = path.join(bidsDir, 'sourcedata', 'stimuli', stim+'.mat')
                task  = logP.split('task-')[-1].split('_run')[0]
                run   = logP.split('run-')[-1].split('_')[0]
                
                makedirs(path.join(outPET, 'stimuli'), exist_ok=True)
                oFname = path.join(outPET, 'stimuli', f'sub-{sub}_ses-{ses}_task-{task}_run-{run}_apertures.nii.gz')
                gazeFile = path.join(bidsDir, 'sourcedata', 'etdata', f'sub-{sub}', f'ses-{ses}', 
                                     f'sub-{sub}_ses-{ses}_task-{task}_run-{run}_gaze.mat')
                
                if not path.isfile(gazeFile):
                    print(f'Gaze file not found at {gazeFile}')
                    print( 'switching off eyetracker correction!')
                    etcorr = False
                
                if not path.isfile(oFname) or force:
                    if not path.isfile(stimP): 
                        exit(f'Did not find stim File: {stimP}')
                        
                    # loat the mat files defining the stimulus
                    imagesFile = loadmat(stimP, simplify_cells=True)
                    paramsFile = loadmat(logP, simplify_cells=True)
                    
                    # get all values necessary
                    seq       = imagesFile['stimulus']['seq']
                    seqTiming = imagesFile['stimulus']['seqtiming']
                    images    = imagesFile['stimulus']['images']
                    tr        = paramsFile['params']['tr']
                    
                    # build and binarise the stimulus
                    stimImagesU, stimImagesUC = np.unique(images, return_counts=True)
                    images[images!=stimImagesU[np.argmax(stimImagesUC)]] = 1
                    images[images==stimImagesU[np.argmax(stimImagesUC)]] = 0
                    oStimVid  = images[:,:, seq[::int(1/seqTiming[1]*tr)]-1] # 8Hz flickering * 2s TR
                    
                    # load the gaze file and do the gaze correction
                    gaze = loadmat(gazeFile, simplify_cells=True)
                    
                    # get rid of out of image data (loss of tracking)
                    gaze['x'][np.any((gaze['x']==0, gaze['x']==1280),0)] = 1280/2 # 1280 comes from resolution of screen
                    gaze['y'][np.any((gaze['y']==0, gaze['y']==1024),0)] = 1024/2 # 1024 comes from resolution of screen
                    # TODO: load the resolution from the _params.mat file?
                    
                    # resamplet to TR
                    x = np.array([np.mean(f) for f in np.array_split(gaze['x'], oStimVid.shape[2])])
                    y = np.array([np.mean(f) for f in np.array_split(gaze['y'], oStimVid.shape[2])])
                    
                    # demean the ET data
                    x -= x.mean()
                    y -= y.mean()
                    y = -y # there is a flip between ET and fixation dot sequece (pixel coordinates), 
                             # with this the ET data is in the same space as fixation dot seq.
                    
                    
                    # TODO: we problably shoud make a border around the actual stim and then 
                    #       place the original stim in the center before shifting it so that
                    #       more peripheral regions could also be stimulated.
                    #       for the analysis the new width (zB 8?? radius)
                    # border = 33 for +1?? radius?
                    # shiftStim = np.zeros((oStimVid.shape[0]+2*border,oStimVid.shape[1]+2*border,oStimVid.shape[2]))
                    
                    # shift the stimulus opposite of gaze direction
                    for i in range(len(x)):
                        oStimVid[...,i] = shift(oStimVid[...,i], (-y[i], -x[i]), mode='constant', cval=0)
                        
                    # save the stimulus as nifti
                    img = nib.Nifti1Image(oStimVid[:,:,None,:].astype('float64'), np.eye(4))
                    img.header['pixdim'][1:5] = [1,1,1,tr]
                    img.header['qoffset_x']=img.header['qoffset_y']=img.header['qoffset_z'] = 1
                    img.header['cal_max'] = 1
                    img.header['xyzt_units'] = 10
                    nib.save(img, oFname)
                        
    return etcorr
