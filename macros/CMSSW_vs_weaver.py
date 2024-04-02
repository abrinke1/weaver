#! /usr/bin/env python

####################################################################################
###  CMSSW_vs_weaver.py : A script to compare CMSSW vs. weaver NN output values  ###
####################################################################################

import ROOT as R
R.gROOT.SetBatch(True)  ## Don't display histograms or canvases when drawn
R.gStyle.SetOptStat(0)  ## Turn off stats box

import os
import sys
import math
import numpy as np

## User-defined constants
INPUT   = 'AWB'  ## Use input files from Si (Higgs mass) or AWB ('a' mass and tagger)
MAX_EVT = 1000     ## Maximum number of events to process
PRT_EVT = 10   ## Print to screen every Nth event
VERBOSE = 0      ## Print extra info about each event
DIFF_H  = 1.00   ## Print extra info for events with large 'H' mass differences
DIFF_A  = 0.03   ## Print extra info for events with large 'a' mass differences
DIFF_T  = 0.001  ## Print extra info for events with large tagger differences

SRCS = ['C','W']         ## Compare CMSSW and weaver
H_ALGS = ['H0','H00','H1','H2','H3','H4','H4x']  ## Compare Higgs mass regression algos
# A_ALGS = ['A2','A3','A4','A4x'] ## Compare 'a' mass regression algos
A_ALGS = ['A0','A1','A2','A3','A4','A4x'] ## Compare 'a' mass regression algos
T_ALGS = ['T1','T2','T3']  ## Compare classifier tagging algos
if (len(sys.argv) > 1 and sys.argv[1] == 'Si') or (len(sys.argv) == 1 and INPUT == 'Si'):
    print('\n*** Running with input files from Si, comparing Higgs mass regression ***\n')
    ALGS = H_ALGS
if (len(sys.argv) > 1 and sys.argv[1] == 'AWB') or (len(sys.argv) == 1 and INPUT == 'AWB'):
    print('\n*** Running with input files from Andrew, comparing m(a) regression and taggers ***\n')
    ALGS = A_ALGS + T_ALGS

## Input files for CMSSW and weaver
Si_dir  = '/home/chosila/Projects/weaver/predict/validation/'
AWB_dir = ' /cms/data/abrinke1/CMSSW/HiggsToAA/ParticleNet/weaver/'
FILES = {}
# FILES['C'] = AWB_dir+'test/HtoAA_addHto4b_HtoAA_MH-125_MA-20_0_10k.root'
# FILES['C'] = AWB_dir+'test/HtoAA_addHto4b_HtoAA_MH-125_MA-20_0_v2_1k.root'
# FILES['C'] = AWB_dir+'test/HtoAA_addHto4b_HtoAA_MH-125_MA-20_0_v3_1k.root'
# FILES['C'] = AWB_dir+'test/HtoAA_addHto4b_HtoAA_MH-125_MA-20_0_v3_test.root'
FILES['C'] = AWB_dir+'test/HtoAA_addHto4b_HtoAA_MH-125_MA-20_0_v4_1k.root'
FILES['W'] = {}
FILES['W']['H0'] = Si_dir+'wide_H_calc_mass_regr_loss3_M20.root'
FILES['W']['H2'] = Si_dir+'wide_H_calc_mass_regr_loss0_M20.root'
FILES['W']['H3'] = Si_dir+'wide_H_calc_logMass_regr_loss0_M20.root'
FILES['W']['H4'] = Si_dir+'wide_H_calc_massOverfj_mass_regr_loss3_M20.root'
FILES['W']['A0'] = AWB_dir+'output/predict_MA-regr_mass_mode3_mH-125_E40_AWB_2023_09_28_Sig_mH-125_mA-20.root'
FILES['W']['A2'] = AWB_dir+'output/predict_MA-regr_mass_mode0_mH-125_E40_AWB_2023_08_31_Sig_mH-125_mA-20.root'
FILES['W']['A3'] = AWB_dir+'output/predict_MA-regr_log_mode0_mH-125_E40_AWB_2023_08_31_Sig_mH-125_mA-20.root'
FILES['W']['A4'] = AWB_dir+'output/predict_MA-regr_ratio_mode3_mH-125_E40_AWB_2023_08_31_Sig_mH-125_mA-20.root'
FILES['W']['T1'] = AWB_dir+'output/predict_multiclass_wH-70_E30_AWB_2023_08_31_Sig_mH-125_mA-20.root'
FILES['W']['T2'] = AWB_dir+'output/predict_binary_wH-70_E30_AWB_2023_08_31_Sig_mH-125_mA-20.root'
FILES['W']['T3'] = AWB_dir+'output/predict_binaryLF_wH-70_E30_AWB_2023_08_31_Sig_mH-125_mA-20.root'


def main():

###################
## Initialize files
###################

    ## Create tree chains from input files
    chC = R.TChain('Events')
    chC.Add(FILES['C'])
    chW = {}
    for alg in ALGS:
        if alg == 'H00': continue  ## Same input file as 'H0'
        if alg ==  'H1': continue  ## Same input file as 'H0'
        if alg == 'H4x': continue  ## Same input file as 'H4'
        if alg ==  'A1': continue  ## Same input file as 'A0'
        if alg == 'A4x': continue  ## Same input file as 'A4'
        chW[alg] = R.TChain('Events')
        chW[alg].Add(FILES['W'][alg])
    chW0 = chW[ALGS[0]]
    
    BASE_STR = 'CMSSW_vs_weaver_v4'
    if H_ALGS[0] in ALGS:
        BASE_STR += '_mH'
    if A_ALGS[0] in ALGS:
        BASE_STR += '_mA'
    if T_ALGS[0] in ALGS:
        BASE_STR += '_Tg'
    if MAX_EVT > 0:
        BASE_STR += '_%dk' % (MAX_EVT / 1000)

    ## Set output directories (create if they do not exist)
    if not os.path.exists('plots/png/%s/' % BASE_STR):
        os.makedirs('plots/png/%s/' % BASE_STR)

    print('Opening output file plots/%s.root' % BASE_STR)
    out_file = R.TFile('plots/%s.root' % BASE_STR, 'recreate')
    png_dir  = 'plots/png/%s/' % BASE_STR

    # Book histograms
    hst = {}
    for alg in ALGS:
        hst[alg] = {}
        hst[alg]['logDiff'] = R.TH1D('%s_logDiff' % alg, '%s_logDiff' % alg, 100, -8, 2)

        
    ##############
    ## Event loops
    ##############

    ## Store values
    vals = {}
    for src in SRCS:
        vals[src] = {}
        for alg in ALGS:
            vals[src][alg] = []

    ## Store event numbers from CMSSW file
    C_evt_no = []
    xMAX_EVT = min(MAX_EVT, chC.GetEntries()) if MAX_EVT > 0 else chC.GetEntries()
    print('\nAbout to store %d event numbers from CMSSW chain' % xMAX_EVT)
    for cEvt in range(xMAX_EVT):
        if (cEvt % (xMAX_EVT / 10)) == 0: print('Event #%d' % cEvt)
        chC.GetEntry(cEvt)
        C_evt_no.append(chC.event)

    ## Find corresponding event indices from weaver file
    W_evt_idx = {}
    print('\nAbout to try to find %d event indices from weaver chain with %d entries' % (len(C_evt_no), chW0.GetEntries()))
    for wEvt in range(chW0.GetEntries()):
        if (wEvt % (chW0.GetEntries() / 10)) == 0: print('Event #%d' % wEvt)
        chW0.GetEntry(wEvt)
        if not chW0.event_no in C_evt_no: continue
        if not chW0.event_no in W_evt_idx.keys():
            W_evt_idx[chW0.event_no] = [wEvt]
        else:
            W_evt_idx[chW0.event_no].append(wEvt)
    print('Found matches for %d out of %d events\n' % (len(W_evt_idx), len(C_evt_no)))

    ## Now loop over CMSSW events to perform the comparison
    print('\nAbout to run over %d events in CMSSW chain\n' % xMAX_EVT)
    for iEvt in range(xMAX_EVT):
        if (iEvt % PRT_EVT) == 0: print('Event #%d' % iEvt)
        chC.GetEntry(iEvt)

        ## Skip event if there is no match in the weaver file
        if not chC.event in W_evt_idx.keys(): continue

        ## Loop over FatJets in CMSSW file
        for iiC in range(chC.nFatJet):
            if chC.FatJet_mass < 1: continue

            if VERBOSE > 2:
                print('\n*** In CMSSW event %d, FatJet[%d] pT = %.1f, eta = %.2f, phi = %.2f, mass = %.1f ***' % ( chC.event, iiC, \
                                                                                                                   chC.FatJet_pt[iiC], \
                                                                                                                   chC.FatJet_eta[iiC], \
                                                                                                                   chC.FatJet_phi[iiC], \
                                                                                                                   chC.FatJet_mass[iiC] ) )

            ## Get corresponding event entries in weaver to find a match to CMSSW event
            for jEvt in W_evt_idx[chC.event]:
                chW0.GetEntry(jEvt)
                if chW0.event_no != chC.event:
                    print('\n\n*** BIZZARE EVENT! W_evt_idx[%d] = %d gives %d!!! Quitting. ***\n\n' % (chC.event, \
                                                                                                       W_evt_idx[chC.event], \
                                                                                                       chW0.event_no) )
                    sys.exit()
                if chW0.jet_no != iiC: continue
                if abs(chC.FatJet_eta[iiC] - chW0.fj_eta) > 0.1: continue
                if abs(chC.FatJet_phi[iiC] - chW0.fj_phi) > 0.1 and \
                   abs(chC.FatJet_phi[iiC] - chW0.fj_phi - 2*3.14159) > 0.1 and \
                   abs(chC.FatJet_phi[iiC] - chW0.fj_phi + 2*3.14159) > 0.1: continue

                ## We have a match! Save values for different algorithms
                if 'H0' in ALGS: vals['C']['H0'].append(chC.FatJet_particleNet_massH_Hto4b_v0[iiC])
                if 'H00' in ALGS: vals['C']['H00'].append(chC.FatJet_particleNet_massH_Hto4b_v00[iiC])
                if 'H1' in ALGS: vals['C']['H1'].append(chC.FatJet_particleNet_massH_Hto4b_v1[iiC])
                if 'H2' in ALGS: vals['C']['H2'].append(chC.FatJet_particleNet_massH_Hto4b_v2[iiC])
                if 'H3' in ALGS: vals['C']['H3'].append(chC.FatJet_particleNet_massH_Hto4b_v3[iiC])
                if 'H4' in ALGS: vals['C']['H4'].append(chC.FatJet_particleNet_massH_Hto4b_v4[iiC])
                if 'H4x' in ALGS: vals['C']['H4x'].append(chC.FatJet_particleNet_massH_Hto4b_v4[iiC])
                if 'A0' in ALGS: vals['C']['A0'].append(chC.FatJet_particleNet_massA_Hto4b_v0[iiC])
                if 'A1' in ALGS: vals['C']['A1'].append(chC.FatJet_particleNet_massA_Hto4b_v1[iiC])
                if 'A2' in ALGS: vals['C']['A2'].append(chC.FatJet_particleNet_massA_Hto4b_v2[iiC])
                if 'A3' in ALGS: vals['C']['A3'].append(chC.FatJet_particleNet_massA_Hto4b_v3[iiC])
                if 'A4' in ALGS: vals['C']['A4'].append(chC.FatJet_particleNet_massA_Hto4b_v4[iiC])
                if 'A4x' in ALGS: vals['C']['A4x'].append(chC.FatJet_particleNet_massA_Hto4b_v4[iiC])
                if 'T1' in ALGS: vals['C']['T1'].append(chC.FatJet_particleNetMD_Hto4b_Haa4b[iiC])
                if 'T2' in ALGS: vals['C']['T2'].append(chC.FatJet_particleNetMD_Hto4b_binary_Haa4b[iiC])
                if 'T3' in ALGS: vals['C']['T3'].append(chC.FatJet_particleNetMD_Hto4b_binaryLF_Haa4b[iiC])

                if 'H0' in ALGS:
                    chW['H0'].GetEntry(jEvt)
                    vals['W']['H0'].append(chW['H0'].output)
                if 'H00' in ALGS:
                    chW['H0'].GetEntry(jEvt)
                    vals['W']['H00'].append(chW['H0'].output)
                if 'H1' in ALGS:
                    chW['H0'].GetEntry(jEvt)
                    vals['W']['H1'].append(chW['H0'].output)
                if 'H2' in ALGS:
                    chW['H2'].GetEntry(jEvt)
                    vals['W']['H2'].append(chW['H2'].output)
                if 'H3' in ALGS:
                    chW['H3'].GetEntry(jEvt)
                    vals['W']['H3'].append(math.exp(chW['H3'].output))
                if 'H4' in ALGS:
                    chW['H4'].GetEntry(jEvt)
                    vals['W']['H4'].append(chW['H4'].output * chC.FatJet_mass[iiC])
                    vals['W']['H4x'].append(chW['H4'].output * chW['H4'].fj_mass)
                if 'A0' in ALGS:
                    chW['A0'].GetEntry(jEvt)
                    vals['W']['A0'].append(chW['A0'].output)
                if 'A1' in ALGS:
                    chW['A0'].GetEntry(jEvt)
                    vals['W']['A1'].append(chW['A0'].output)
                if 'A2' in ALGS:
                    chW['A2'].GetEntry(jEvt)
                    vals['W']['A2'].append(chW['A2'].output)
                if 'A3' in ALGS:
                    chW['A3'].GetEntry(jEvt)
                    vals['W']['A3'].append(math.exp(chW['A3'].output))
                if 'A4' in ALGS:
                    chW['A4'].GetEntry(jEvt)
                    vals['W']['A4'].append(chW['A4'].output * chC.FatJet_mass[iiC])
                    vals['W']['A4x'].append(chW['A4'].output * chW['A4'].fj_mass)
                if 'T1' in ALGS:
                    chW['T1'].GetEntry(jEvt)
                    vals['W']['T1'].append(chW['T1'].probHaa4b)
                if 'T2' in ALGS:
                    chW['T2'].GetEntry(jEvt)
                    vals['W']['T2'].append(chW['T2'].probHaa4b)
                if 'T3' in ALGS:
                    chW['T3'].GetEntry(jEvt)
                    vals['W']['T3'].append(chW['T3'].probHaa4b)

                ## Check for maximum differences
                max_diff_H = -1
                max_diff_A = -1
                max_diff_T = -1
                for alg in ALGS:
                    this_diff = vals['C'][alg][-1] - vals['W'][alg][-1]
                    if alg in ['H2','H3','H4']:
                        max_diff_H = max(max_diff_H, abs(this_diff))
                    if alg.startswith('A') and not alg.endswith('x'):
                        max_diff_A = max(max_diff_A, abs(this_diff))
                    if alg.startswith('T'):
                        max_diff_T = max(max_diff_T, abs(this_diff))
                    hst[alg]['logDiff'].Fill( max(min(math.log10(abs(this_diff)+pow(10,-10)), 1.999), -7.999) )

                ## Printouts
                if VERBOSE == 2 or max_diff_H > DIFF_H or max_diff_A > DIFF_A or max_diff_T > DIFF_T:
                    print('\n*** In CMSSW event %d, FatJet[%d] pT = %.1f, eta = %.2f, phi = %.2f, mass = %.1f ***' % ( chC.event, iiC, \
                                                                                                                       chC.FatJet_pt[iiC], \
                                                                                                                       chC.FatJet_eta[iiC], \
                                                                                                                       chC.FatJet_phi[iiC], \
                                                                                                                       chC.FatJet_mass[iiC] ) )
                if VERBOSE >= 2 or max_diff_H > DIFF_H or max_diff_A > DIFF_A or max_diff_T > DIFF_T:
                    print(' - In weaver event %d, FatJet[%d] pT = %.1f, eta = %.2f, phi = %.2f, mass = %.1f' % ( chW0.event_no, chW0.jet_no, \
                                                                                                                 chW0.fj_pt, chW0.fj_eta, \
                                                                                                                 chW0.fj_phi, chW0.fj_mass ) )
                if VERBOSE >= 1 or max_diff_H > DIFF_H or max_diff_A > DIFF_A or max_diff_T > DIFF_T:
                    print('$$$ CMSSW vs. weaver: max_diff_H = %.6f, max_diff_A = %.6f, max_diff_T = %.6f' % (max_diff_H, max_diff_A, max_diff_T))
                    for alg in ALGS:
                        print(' - %s %.6f vs. %.6f' % (alg, vals['C'][alg][-1], vals['W'][alg][-1]))

                ## Now that we've found a match, move on to next CMSSW jet
                break

            ## End loop: for jEvt in range(chW.GetEntries())
        ## End loop: for iiC in range(chC.nFatJet)
    ## End loop: for iEvt in range(chC.GetEntries())

    print('\nAll done!!!\n')

    out_file.cd()

    c0 = R.TCanvas('c0')
    c0.cd()

    for alg in ALGS:
        ## Print out useful summary information
        valC = np.array(vals['C'][alg])
        valW = np.array(vals['W'][alg])
        if VERBOSE > 0:
            print(valC - valW)
            print((valC - valW) / valW)
        print('\n%s max deviation out of %d jets: %.6f (%.4f%%)' % (alg, len(valC), max(abs(valC - valW)), \
                                                                    100*max((abs(valC - valW)) / valW)))
        ## Save plots
        hst[alg]['logDiff'].SetLineWidth(2)
        hst[alg]['logDiff'].SetLineColor(R.kBlack)
	hst[alg]['logDiff'].Write()
        hst[alg]['logDiff'].Draw('hist')
        alg_name = alg.replace('H', 'Mass(H) regression v')
        alg_name = alg_name.replace('A', 'Mass(a) regression v')
        alg_name = alg_name.replace('T', 'Tagger v')
        hst[alg]['logDiff'].SetTitle('%s - CMSSW vs. weaver' % (alg_name))
        hst[alg]['logDiff'].GetXaxis().SetTitle('log_{10} of absolute difference')
        hst[alg]['logDiff'].GetYaxis().SetTitle('# of jets')
        c0.SaveAs(png_dir+'h_logDiff_%s.png' % alg)
        c0.SetLogy()
        hst[alg]['logDiff'].GetYaxis().SetTitle('log(# of jets)')
	c0.SaveAs(png_dir+'h_logDiff_%s_log.png' % alg)
	c0.SetLogy(0)
        c0.Clear()
    ## End loop: for alg in ALGS

    out_file.Write()

    del c0
    del out_file

## Define 'main' function as primary executable
if __name__ == '__main__':
    main()
