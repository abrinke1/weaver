#! /usr/bin/env python

##############################################################
###  ROC.py : a script to plot ROC curves from flat trees  ###
##############################################################

import ROOT as R
R.gROOT.SetBatch(True)  ## Don't display histograms or canvases when drawn
R.gStyle.SetOptStat(0)  ## Turn off stats box

import os
import sys
import math
import copy
import subprocess

## User-defined constants
MAX_EVT = -1      ## Maximum number of events to process
PRT_EVT = 100000  ## Print to screen every Nth event
VERBOSE = False   ## Print extra info about each event
DO_EVT  = True  ## Re-compute underlying 1D histograms

# PNET = 'multiclass_wH-70_E30_AWB_2023_05_30'
# PNET = 'multiclass_QCD_wH-70_E30_AWB_2024_04_04'
PNET = 'ultraclass_wH-70_E20_AWB_2024_04_04'
SIGS = ['Hto4b_mH_125', 'Hto4b_mH_125_mAHi', 'Hto4b_wH_70', 'Hto4b_wH_70_mHIn']
# BKGS = ['QCD', 'QCD_mHIn', 'QCD_2b', 'QCD_3b', 'QCD_4b']
# BKGS = ['QCD', 'QCD_2b', 'QCD_3b', 'QCD_4b']
BKGS = ['QCD', 'QCD_mHIn', 'TT', 'TT_mHIn', 'ZtoQQ', 'ZtoQQ_mHIn']
VARS = ['PN_Xto4b',      ## score_label_H_aa_bbbb or probHaa4b
        'PN_Xto4bVsQCD', ## score_label_H_aa_bbbb or probHaa4b over probHaa4b+probQCD
        'PN_Xto4bVsNR',  ## score_label_H_aa_bbbb or probHaa4b over probHaa4b+probNR
        'PN_Xto4bVsISR', ## score_label_H_aa_bbbb or probHaa4b over probHaa4b+probISR
        'PN_Xto4bVsAll'] ## score_label_H_aa_bbbb or probHaa4b over probHaa4b+probQCD+probNR+probISR
        # 'PN_Xto4q', ## pfParticleNetDiscriminatorsJetTags_H4qvsQCD
        # 'PN_Xto2b', ## pfMassDecorrelatedParticleNetDiscriminatorsJetTags_XbbvsQCD
        # 'PF_Xto2b'] ## fj_doubleb


def main():

###################
## Initialize files
###################

    ## Location of input files
    in_file_names = []
    in_dir = '/cms/data/abrinke1/CMSSW/HiggsToAA/ParticleNet/weaver/output/'
    ## CAREFUL!!! Later code depends on mH_125 being first, wH-70 being 2nd,
    ## also on TT being 4th and ZtoQQ being 5th (search for iCh)
    ## Also note this cut which excludes other processes: is_QCD or is_mH125 or is_wH70
    in_file_names.append(in_dir+'predict_%s_Sig_mH-125.root' % PNET)
    in_file_names.append(in_dir+'predict_%s_Sig_wH-70.root' % PNET)
    in_file_names.append(in_dir+'predict_%s_QCD.root' % PNET)
    in_file_names.append(in_dir+'predict_%s_TT.root' % PNET)
    in_file_names.append(in_dir+'predict_%s_ZtoQQ.root' % PNET)

    ## Chain together trees from input files
    in_chains = []
    for i in range(len(in_file_names)):
        print('Opening file: '+in_file_names[i])
        in_chains.append( R.TChain('Events') )
        in_chains[i].Add( in_file_names[i] )

    BASE_STR = 'ROC_'+PNET.replace('-','_')+'_'
    for VAR in VARS:
        BASE_STR += ('_'+VAR)
    if MAX_EVT > 0:
        BASE_STR += '_%dk' % (MAX_EVT / 1000)

    ## Set output directories (create if they do not exist)
    if not os.path.exists('plots/png/%s/' % BASE_STR):
        os.makedirs('plots/png/%s/' % BASE_STR)

    print('Opening output file plots/%s.root' % BASE_STR)
    out_file = R.TFile('plots/%s.root' % BASE_STR, ('recreate' if DO_EVT else 'update'))
    png_dir  = 'plots/png/%s/' % BASE_STR


    #############
    ## Histograms
    #############

    if DO_EVT:
        ## Histogram bins: [# of bins, minimum x, maximum x]
        NN_bins = [1000, 0, 1]

        ## Book 1D histogram
        ## Important to use '1D' instead of '1F' when dealing with large numbers of entries, and weighted events (higher precision)
        h_1D = {}
        for VAR in VARS:
            h_1D[VAR] = {}
            for SAMP in SIGS+BKGS:
                h_1D[VAR][SAMP] = {}
                for TRTE in ['tr','te']:
                    h_1D[VAR][SAMP][TRTE] = R.TH1D('x', 'x', NN_bins[0], NN_bins[1], NN_bins[2])
                    h_1D[VAR][SAMP][TRTE].SetName('h_%s_%s_%s' % (VAR, SAMP, TRTE))
                    h_1D[VAR][SAMP][TRTE].SetTitle('%s %s (%s)' % (SAMP, VAR, TRTE))

    ## Graphs for ROC curves
    g_ROC = {}
    for VAR in VARS:
        g_ROC[VAR] = {}
        for SIG in SIGS:
            g_ROC[VAR][SIG] = {}
            for BKG in BKGS:
                g_ROC[VAR][SIG][BKG] = {}
                for TRTE in ['tr','te']:
                    g_ROC[VAR][SIG][BKG][TRTE] = R.TGraph()
                    g_ROC[VAR][SIG][BKG][TRTE].SetName('g_%s_%s_vs_%s_%s' % (VAR, SIG, BKG, TRTE))
            

    #############
    ## Event loop
    #############
    iCh     = 0  ## Chain index
    iEvt    = 0  ## Event index
    iEvtWgt = 0. ## Weighted event integral
    for ch in in_chains:

        if not DO_EVT: break
        iCh += 1
        if iEvt >= MAX_EVT*iCh and MAX_EVT > 0: break

        print('\nAbout to run over %d events in chain\n' % (ch.GetEntries()))
                
        for jEvt in range(ch.GetEntries()):

            if iEvt >= MAX_EVT*iCh and MAX_EVT > 0: break
            iEvt += 1
            if iEvt % PRT_EVT is 0: print('Event #%d' % iEvt)

            ch.GetEntry(ch.GetEntries()-jEvt)

            ## Event cuts from the weaver NTuples, also applied in
            ## data/Hto4b_ak8_points_pf_sv_full_wH-70_multiclass.yaml
            if ch.fj_pt <=  170: continue
            if ch.fj_mass <= 50: continue
            # if ch.fj_pt >= 1000: continue  ## For 2023_05_30 training
            # if ch.pfMassDecorrelatedParticleNetDiscriminatorsJetTags_XbbvsQCD <= 0.1: continue  ## For 2023_05_30 training
            if ch.fj_pt >= 7000: continue  ## For 2024 training
            if ch.fj_sdmass <= 10: continue  ## For 2024 training

            ## Store probability scores
            probHaa4b = ch.probHaa4b
            # probQCD = ch.probQCD0b + ch.probQCD1b + ch.probQCD2b + ch.probQCD3b + ch.probQCD4b
            probQCD = ch.probQCD0b + ch.probQCD1b + ch.probQCD2b + ch.probQCD2b2c + ch.probQCD3b + ch.probQCD4b
            probISR = ch.probISR0b + ch.probISR1b + ch.probISR2b + ch.probISR2b2c + ch.probISR3b + ch.probISR4b
            probNR = ch.probNR0b + ch.probNR1b + ch.probNR2b + ch.probNR2b2c + ch.probNR3b + ch.probNR4b + ch.probNRlep

            VALS = {}
            # VALS['PN_Xto4b'] = ch.score_label_H_aa_bbbb
            VALS['PN_Xto4b'] = probHaa4b
            VALS['PN_Xto4bVsQCD'] = (probHaa4b / max(probHaa4b + probQCD, 0.01))
            VALS['PN_Xto4bVsISR'] = (probHaa4b / max(probHaa4b + probISR, 0.01))
            VALS['PN_Xto4bVsNR']  = (probHaa4b / max(probHaa4b + probNR, 0.01))
            VALS['PN_Xto4bVsAll'] = (probHaa4b / max(probHaa4b + probQCD + probISR + probNR, 0.01))
            # VALS['PN_Xto4q'] = ch.pfParticleNetDiscriminatorsJetTags_H4qvsQCD
            # VALS['PN_Xto2b'] = ch.pfMassDecorrelatedParticleNetDiscriminatorsJetTags_XbbvsQCD
            VALS['PF_Xto2b'] = ch.fj_doubleb

            is_QCD   = ch.sample_isQCD
            # is_mH125  = (ch.label_H_aa_bbbb and abs(ch.fj_gen_mass - 125.) < 0.2)
            # is_wH70   = (ch.label_H_aa_bbbb and abs(ch.fj_gen_mass - 125.) > 0.2)
            is_mH125  = (ch.label_H_aa_bbbb and iCh == 1 and ch.fj_gen_H_aa_bbbb_mass_a2 > 11.9)
            is_wH70   = (ch.label_H_aa_bbbb and iCh == 2)
            is_TT     = (iCh == 4)
            is_ZtoQQ  = (iCh == 5)

            # is_QCD_2b = ch.label_QCD_2b
            # is_QCD_3b = ch.label_QCD_3b
            # is_QCD_4b = ch.label_QCD_4b
            is_QCD_2b = ch.QCD2b
            is_QCD_3b = ch.QCD3b
            is_QCD_4b = ch.QCD4b

            is_wH70_mHIn  = is_wH70  and ch.fj_mass > 100 and ch.fj_mass < 140
            # is_mH125_mAHi = is_mH125 and ch.fj_gen_H_aa_bbbb_mass_a > 22.5  ## For 2023_05_30 training
            is_mH125_mAHi = is_mH125 and ch.fj_gen_H_aa_bbbb_mass_a2 > 22.5
            is_QCD_mHIn   = is_QCD   and ch.fj_mass > 100 and ch.fj_mass < 140
            is_TT_mHIn    = is_TT    and ch.fj_mass > 100 and ch.fj_mass < 140
            is_ZtoQQ_mHIn = is_ZtoQQ and ch.fj_mass > 100 and ch.fj_mass < 140

            # train = (((ch.event_no % 101) % 2) == 0)  ## For 2023_05_30 training
            train = ((ch.event_no % 2) == 0)  ## For 2024 trainings

            if not (is_QCD or is_mH125 or is_wH70 or is_TT or is_ZtoQQ): continue

            WGT = ch.event_weight_wH70
            iEvtWgt += WGT


            ###################################
            ###  Fill per-event histograms  ###
            ###################################

            for VAR in VARS:
                for SIG in SIGS:
                    if (is_mH125 and SIG == 'Hto4b_mH_125') or (is_mH125_mAHi and SIG == 'Hto4b_mH_125_mAHi') or \
                       (is_wH70 and SIG == 'Hto4b_wH_70') or (is_wH70_mHIn and SIG == 'Hto4b_wH_70_mHIn'):
                        h_1D[VAR][SIG]['tr' if train else 'te'].Fill( VALS[VAR], WGT )
                for BKG in BKGS:
                    if (is_QCD and BKG == 'QCD') or (is_QCD_mHIn and BKG == 'QCD_mHIn') or \
                       (is_QCD_2b and BKG == 'QCD_2b') or (is_QCD_3b and BKG == 'QCD_3b') or (is_QCD_4b and BKG == 'QCD_4b') or \
                       (is_TT and BKG == 'TT') or (is_TT_mHIn and BKG == 'TT_mHIn') or \
                       (is_ZtoQQ and BKG == 'ZtoQQ') or (is_ZtoQQ_mHIn and BKG == 'ZtoQQ_mHIn'):
                        h_1D[VAR][BKG]['tr' if train else 'te'].Fill( VALS[VAR], WGT )

            ## End loop over variables (VAR)

        ## End loop over events in chain (jEvt)
    ## End loop over chains (ch)

    print('\n\nProcessed %d total events (%.2f weighted)' % (iEvt, iEvtWgt))


    ######################
    ## Save the histograms
    ######################

    colors = {}
    colors['Hto4b_mH_125']      = R.kGreen+3
    colors['Hto4b_mH_125_mAHi'] = R.kGreen
    colors['Hto4b_wH_70']       = R.kRed
    colors['Hto4b_wH_70_mHIn']  = R.kMagenta
    colors['QCD']               = R.kBlue
    colors['QCD_mHIn']          = R.kViolet
    colors['QCD_2b']            = R.kBlue-7
    colors['QCD_3b']            = R.kCyan+1
    colors['QCD_4b']            = R.kCyan+3
    colors['TT']                = R.kBlue-7
    colors['TT_mHIn']           = R.kCyan+3
    colors['ZtoQQ']             = R.kOrange+10
    colors['ZtoQQ_mHIn']        = R.kOrange+3
    colors['PN_Xto4b']          = R.kRed
    colors['PN_Xto4bVsQCD']     = R.kPink-7
    colors['PN_Xto4bVsISR']     = R.kBlue
    colors['PN_Xto4bVsNR']      = R.kViolet
    colors['PN_Xto4bVsAll']     = R.kGreen
    colors['PN_Xto4q']          = R.kBlue
    colors['PN_Xto2b']          = R.kViolet
    colors['PF_Xto2b']          = R.kGreen

    out_file.cd()

    ## ----------------------
    ## Fill the 1D histograms
    ## ----------------------
    if DO_EVT:
        c0 = R.TCanvas('c0')
        c0.cd()

        for VAR in VARS:
            for SAMP in SIGS+BKGS:
                h_1D[VAR][SAMP]['tr'].SetLineWidth(2)
                h_1D[VAR][SAMP]['tr'].SetLineColor(R.kBlack)
                h_1D[VAR][SAMP]['tr'].Write()
                h_1D[VAR][SAMP]['tr'].Draw('hist')
                h_1D[VAR][SAMP]['te'].SetLineWidth(2)
                h_1D[VAR][SAMP]['te'].SetLineColor(colors[SAMP])
                h_1D[VAR][SAMP]['te'].Write()
                h_1D[VAR][SAMP]['te'].Draw('histsame')
                c0.SaveAs(png_dir+'h_%s_%s.png' % (VAR, SAMP))
                c0.SetLogy()
                c0.SaveAs(png_dir+'h_%s_%s_log.png' % (VAR, SAMP))
                c0.SetLogy(0)
                c0.Clear()
            ## End loop: for SAMP in SIGS+BKGS
        ## End loop: for VAR in VARS
    ## End conditional: if DO_EVT


    ## -------------------
    ## Fill the ROC curves
    ## -------------------
    c1 = R.TCanvas('c1')
    c1.cd()

    for VAR in VARS:
        for SIG in SIGS:
            for BKG in BKGS:
                legA = R.TLegend(0.12,0.58,0.42,0.88)
                for TRTE in ['tr','te']:
                    print('Filling ROC %s' % g_ROC[VAR][SIG][BKG][TRTE].GetName())
                    h_s = out_file.Get('h_%s_%s_%s' % (VAR, SIG, TRTE))
                    h_b = out_file.Get('h_%s_%s_%s' % (VAR, BKG, TRTE))
                    n_s = h_s.Integral()
                    n_b = h_b.Integral()
                    nBins = h_s.GetNbinsX()
                    for ii in range(nBins+1):
                        f_s = h_s.Integral(nBins-ii, nBins) / n_s
                        f_b = h_b.Integral(nBins-ii, nBins) / n_b
                        nPts = g_ROC[VAR][SIG][BKG][TRTE].GetN()
                        g_ROC[VAR][SIG][BKG][TRTE].SetPoint(nPts, f_s, f_b)

                    g_ROC[VAR][SIG][BKG][TRTE].GetYaxis().SetRangeUser(0.0001, 1.0)
                    g_ROC[VAR][SIG][BKG][TRTE].SetTitle('%s ROC curve (%s vs. %s)' % (VAR, SIG, BKG))
                    g_ROC[VAR][SIG][BKG][TRTE].GetXaxis().SetTitle('%s signal efficiency' % SIG)
                    g_ROC[VAR][SIG][BKG][TRTE].GetYaxis().SetTitle('%s background efficiency' % BKG)
                    g_ROC[VAR][SIG][BKG][TRTE].SetMarkerColor(colors[SIG] if TRTE == 'te' else R.kBlack)
                    g_ROC[VAR][SIG][BKG][TRTE].SetLineColor(colors[SIG] if TRTE == 'te' else R.kBlack)
                    g_ROC[VAR][SIG][BKG][TRTE].SetLineWidth(2)
                    g_ROC[VAR][SIG][BKG][TRTE].Write()
                    ## Overlay train + test ROCs of same sig-bkg combination
                    g_ROC[VAR][SIG][BKG][TRTE].Draw('AL' if TRTE == 'tr' else 'Lsame')
                    legA.AddEntry(g_ROC[VAR][SIG][BKG][TRTE], '%s (%s)' % (VAR, 'train' if TRTE == 'tr' else 'test'))
                    del h_s
                    del h_b
                ## End loop: for TRTE in ['tr','te']
                legA.Draw('same')
                c1.SaveAs(png_dir+'g_%s_%s_vs_%s.png' % (VAR, SIG, BKG))
                c1.SetLogy()
                # legA.SetX1NDC(0.58)
                # legA.SetX2NDC(0.88)
                # legA.SetY1NDC(0.12)
                # legA.SetY2NDC(0.42)
                c1.SaveAs(png_dir+'g_%s_%s_vs_%s_log.png' % (VAR, SIG, BKG))
                c1.SetLogy(0)
                c1.Clear()
                del legA
            ## End loop: for BKG in BKGS
        ## End loop: for SIG in SIGS

        
        ## Overlay test ROCs of all sig combinations
        for BKG in BKGS:
            legB = R.TLegend(0.12,0.58,0.42,0.88)
            for SIG in SIGS:
                if SIG == SIGS[0]:
                    g_ROC[VAR][SIG][BKG]['te'].SetTitle('%s ROC curve (vs. %s)' % (VAR, BKG))
                    g_ROC[VAR][SIG][BKG]['te'].GetXaxis().SetTitle('Signal efficiencies')
                g_ROC[VAR][SIG][BKG]['te'].Draw('AL' if (SIG == SIGS[0]) else 'Lsame')
                legB.AddEntry(g_ROC[VAR][SIG][BKG]['te'], '%s' % SIG)
            legB.Draw('same')
            c1.SaveAs(png_dir+'g_%s_all_vs_%s.png' % (VAR, BKG))
            c1.SetLogy()
            # legB.SetX1NDC(0.58)
            # legB.SetX2NDC(0.88)
            # legB.SetY1NDC(0.12)
            # legB.SetY2NDC(0.42)
            c1.SaveAs(png_dir+'g_%s_all_vs_%s_log.png' % (VAR, BKG))
            c1.SetLogy(0)
            c1.Clear()
            del legB

        ## Overlay test ROCs of all bkg combinations
        for SIG in SIGS:
            legC = R.TLegend(0.12,0.58,0.42,0.88)
            for BKG in BKGS:
                if BKG == BKGS[0]:
                    g_ROC[VAR][SIG][BKG]['te'].SetTitle('%s ROC curve (%s)' % (VAR, SIG))
                    g_ROC[VAR][SIG][BKG]['te'].GetYaxis().SetTitle('Background efficiencies')
                g_ROC[VAR][SIG][BKG]['te'].SetLineColor(colors[BKG])
                g_ROC[VAR][SIG][BKG]['te'].Draw('AL' if (BKG == BKGS[0]) else 'Lsame')
                legC.AddEntry(g_ROC[VAR][SIG][BKG]['te'], 'vs. %s' % BKG)
            legC.Draw('same')
            c1.SaveAs(png_dir+'g_%s_%s_vs_all.png' % (VAR, SIG))
            c1.SetLogy()
            # legC.SetX1NDC(0.58)
            # legC.SetX2NDC(0.88)
            # legC.SetY1NDC(0.12)
            # legC.SetY2NDC(0.42)
            c1.SaveAs(png_dir+'g_%s_%s_vs_all_log.png' % (VAR, SIG))
            c1.SetLogy(0)
            c1.Clear()
            del legC

    ## End loop: for VAR in VARS
    
    ## Overlay test ROCs of all variables
    for SIG in SIGS:
        for BKG in BKGS:
            legD = R.TLegend(0.12,0.58,0.42,0.88)
            for VAR in VARS:
                if VAR == VARS[0]:
                    g_ROC[VAR][SIG][BKG]['te'].SetTitle('ROC curves (%s vs. %s)' % (SIG, BKG))
                    g_ROC[VAR][SIG][BKG]['te'].GetYaxis().SetTitle('%s background efficiency' % BKG)
                    g_ROC[VAR][SIG][BKG]['te'].GetXaxis().SetTitle('%s signal efficiency' % SIG)
                g_ROC[VAR][SIG][BKG]['te'].SetLineColor(colors[VAR])
                g_ROC[VAR][SIG][BKG]['te'].Draw('AL' if (VAR == VARS[0]) else 'Lsame')
                legD.AddEntry(g_ROC[VAR][SIG][BKG]['te'], '%s' % VAR)
            legD.Draw('same')
            c1.SaveAs(png_dir+'g_all_%s_vs_%s.png' % (SIG, BKG))
            c1.SetLogy()
            # legD.SetX1NDC(0.58)
            # legD.SetX2NDC(0.88)
            # legD.SetY1NDC(0.12)
            # legD.SetY2NDC(0.42)
            c1.SaveAs(png_dir+'g_all_%s_vs_%s_log.png' % (SIG, BKG))
            c1.SetLogy(0)
            c1.Clear()

    del out_file


## Define 'main' function as primary executable
if __name__ == '__main__':
    main()
