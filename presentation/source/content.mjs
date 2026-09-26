import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const here = path.dirname(fileURLToPath(import.meta.url));
export const eeg = JSON.parse(fs.readFileSync(path.join(here, 'eeg.json')));
export const C = {bg:'#F5F3ED',ink:'#1A2924',green:'#006D46',bright:'#00ED64',muted:'#5B6861',line:'#CFD6CB',pale:'#E5EBE0',white:'#FFFFFF'};
const text = (text,x,y,w,h,size=36,extra={}) => ({type:'text',text,x,y,w,h,size,color:C.ink,font:'Source Sans 3',weight:400,...extra});
const head = (value,x,y,w,h,size=104,extra={})=>text(value,x,y,w,h,size,{font:'Space Grotesk',weight:500,...extra});
const line=(x,y,w,color=C.line)=>({type:'line',x,y,w,h:1,color});
const image=(src,x,y,w,h,alt,extra={})=>({type:'image',src,x,y,w,h,alt,...extra});
const shell=(n,label)=>[
 image('assets/second-shift.svg',96,54,48,48,'Second Shift wave mark'),
 text('Second Shift',162,59,360,44,31,{font:'Space Grotesk',weight:600}),
 text(label,1300,64,524,40,25,{align:'right',color:C.muted}),
 line(96,993,1728),
 text('NEURO AI',96,1012,600,35,23,{weight:600,color:C.green}),
 text(String(n).padStart(2,'0')+' / 06',1660,1012,164,35,23,{align:'right',color:C.muted})
];
export const slides = [
 {id:'opening',title:'Second Shift',start:0,duration:12,notes:'We built Second Shift, a neuroscience harness that keeps EEG research moving when an agent crashes or loses its working context.',sources:['README.md: What it does','Conceptual artwork generated with built-in image_gen. Electrode placement is illustrative, not a measured montage.'],elements:[
  ...shell(1,'MongoDB × Cerebral Valley'),
  image('assets/brain-hero-alpha.png',932,135,910,850,'Conceptual porcelain brain sculpture with green electrode contacts',{motion:'sculpture',fit:'contain'}),
  text('AUTONOMOUS NEUROSCIENCE RESEARCH',96,240,810,44,25,{color:C.green,weight:600}),
  head('Second',89,305,840,188,176),head('Shift',89,477,770,190,176),
  text('A neuroscience harness\nfor recorded brain signals.',98,710,770,138,49,{lineHeight:1.18}),
  text('Andrew Shatsky and David Shatsky',98,914,780,40,26,{color:C.muted}),
 ]},
 {id:'signals',title:'Finding patterns in brain signals',start:12,duration:15,notes:'EEG records electrical activity from the scalp. Our task is to distinguish imagined fists from imagined feet. The agent searches 225 configurations, and each measured result helps guide its next experiment.',sources:['harness/contracts.py: 225 effective configurations','harness/eeg.py: within-subject run 6 training, run 10 validation, run 14 sealed test','PhysioNet EEG Motor Movement/Imagery v1.0.0: https://physionet.org/content/eegmmidb/1.0.0/','Plot: S001R06.edf, channel C3, first T1 cue at 12.5 seconds, unfiltered 160 Hz samples. See source/eeg.json.'],elements:[
  ...shell(2,'The research question'),
  head('Finding patterns in\nbrain signals',96,155,1430,242,106),
  text('Imagined fists or imagined feet?',98,420,1210,75,53,{weight:600}),
  text('Electrical activity recorded from the scalp',98,503,1140,48,33,{color:C.muted}),
  {type:'chart',x:96,y:618,w:1040,h:225,data:eeg},
  text('Real EEG excerpt · C3 · amplitude in µV',98,870,1050,40,27,{color:C.muted}),
  line(1222,457,598),
  head('225',1226,503,580,206,170,{color:C.green}),
  text('possible experiment configurations',1230,731,580,92,36),
  text('Electrodes, frequency bands,\ntime windows, classifiers',1230,848,580,98,30,{color:C.muted})
 ]},
 {id:'mechanism',title:'How Second Shift researches',start:27,duration:18,notes:'Each decision starts with evidence from Atlas. Exact reads retrieve measured results. Vector search retrieves notes. Claude chooses the next experiment, and numerical code evaluates it. The result returns to Atlas for the next decision.',sources:['harness/worker.py','harness/context.py: exact reads of best, leaders, laggards, recent results; semantic retrieval over notes','harness/store.py: deduplication, protocol identity, lease-fenced commits','harness/eeg.py: numerical evaluation'],elements:[
  ...shell(3,'The research loop'),head('How Second Shift\nresearches',96,155,1500,245,106),
  text('Fresh context for every experiment',98,419,1560,62,42,{color:C.muted}),
  head('01',100,543,230,100,71,{color:C.green,motion:'worker-step'}),head('02',702,543,230,100,71,{color:C.green}),head('03',1304,543,230,100,71,{color:C.green}),
  head('Remember',100,657,522,75,59,{motion:'worker-step'}),head('Decide',702,657,540,75,59),head('Experiment',1304,657,540,75,56),
  text('Exact results and relevant notes',100,754,516,55,33,{color:C.muted,motion:'worker-step'}),text('Claude plans via OpenRouter',702,754,542,55,32,{color:C.muted}),text('Code measures EEG accuracy',1304,754,522,55,32,{color:C.muted}),
  {type:'connector',x:525,y:585,w:115,h:1,color:C.green},{type:'connector',x:1130,y:585,w:114,h:1,color:C.green},
  text('Each decision rebuilds context within a 4,000 token budget',100,820,1500,36,26,{color:C.green}),
  {type:'memory',x:100,y:868,w:1720,h:64},
  text('Atlas stores results. Jev routes notes. Voyage embeds them.',120,880,1630,40,30,{align:'center',color:C.green,weight:600})
 ]},
 {id:'demo',title:'The working system',start:45,duration:95,playAt:50,cue:'At 0:50, press Enter. Let the 90-second narration play without speaking over it. Advance when the video ends at 2:20.',notes:'Watch the saved results survive a restart and a tighter electrode limit.',sources:['presentation/second-shift-neuroai-90s.mp4: 90 seconds, campaign camp_639cfbea, original narration preserved','run/video-v6/export/edit-decisions.json and transcript-review.json','run/video-v6/take-1/recovery-proof.json: interrupted experiment resumes as attempt 2'],elements:[
  ...shell(4,'90-second narrated demo'),
  head('The working\nsystem',96,188,1600,270,125),
  text('Saved results survive a restart.\nThe electrode limit drops from 64 to 9.',100,530,1340,145,51,{lineHeight:1.2}),
  {type:'video',x:0,y:0,w:1920,h:1080,src:'media/second-shift-neuroai-90s.mp4'},
  text('Press Enter to play',100,837,1100,55,35,{color:C.green,weight:600}),
 ]},
 {id:'evidence',title:'Results and reliability',start:140,duration:22,notes:'The demo reaches seventy five point nine percent validation balanced accuracy using nine electrodes. Separately, our reference campaign scored seventy three point two percent on its sealed test using twenty one electrodes. These are small offline experiments, supported by separate reliability checks.',sources:['presentation/second-shift-neuroai-90s.mp4 at 1:26–1:29: 0.759 best eligible validation score with 9 electrodes','run/video-v6/take-1/experiments.json: camp_639cfbea, central9, val_balanced_accuracy 0.7592, n_val 75','README.md: camp_0f8981ee, 0.774 validation, 0.732 sealed test, 21 electrodes, 75 test trials, subjects 1–5','eval/checks.json: camp_51b0f538 recovery 8/8; camp_66e4900c constraint 5/5','Validation guides model selection. The 73.2% sealed test result and reliability checks come from separate campaigns, not the demo.'],elements:[
  ...shell(5,'Demo and separate evaluations'),head('Results and reliability',96,154,1730,143,105),
  text('DEMO CAMPAIGN: 9 ELECTRODES',100,370,1000,44,27,{color:C.green,weight:600}),
  head('75.9%',87,434,1060,281,235,{color:C.green}),
  text('validation balanced accuracy',100,739,1060,73,48),
  text('After restart and the new electrode limit',100,842,1080,46,30,{color:C.muted}),
  line(1270,375,554),text('SEPARATE REFERENCE CAMPAIGN',1270,400,555,44,25,{color:C.muted,weight:600}),
  head('73.2%',1264,466,540,125,102),text('sealed test balanced accuracy',1270,603,552,49,32),
  text('21 electrodes, 5 participants\n75 test trials, scored once',1270,672,550,86,28,{color:C.muted}),
  text('SEPARATE RELIABILITY CHECKS',1270,791,555,40,25,{color:C.muted,weight:600}),
  text('8/8 recovery checks passed\n5/5 constraint checks passed',1270,844,552,86,31),
  text('Offline research prototype. Clinical use and live decoding remain outside scope.',100,937,1430,34,23,{color:C.muted})
 ]},
 {id:'closing',title:'Research that keeps its progress',start:162,duration:13,notes:'We tested memory with ten thousand distractor notes. Billions of tokens remains the goal. Second Shift keeps research moving, even when the agent starts over. Thank you.',sources:['eval/stress.json: 10,000 synthetic distractor notes in a copied real campaign','eval/stress_current_packet.json: 10,009 total memories, estimated 1,204 tokens within a 4,000 token budget','README.md: billions of tokens is a target, not an achieved scale','README.md: project scope and team','Repository: https://github.com/uyqv/MongoDB-Hackathon','Conceptual brain and evidence-layer artwork generated with built-in image_gen.'],elements:[
  ...shell(6,'Second Shift'),
  image('assets/brain-memory-alpha.png',968,150,884,826,'Conceptual brain sculpture above persistent layers of experimental evidence',{motion:'sculpture',fit:'contain'}),
  head('Research that\nkeeps its\nprogress',96,211,970,360,107),
  text('Tested with 10,000 distractor notes.\nBillions of tokens is the long term target.',100,631,910,133,38,{color:C.muted,lineHeight:1.2}),
  text('Andrew Shatsky and David Shatsky',100,842,850,51,31,{weight:600}),
  text('github.com/uyqv/MongoDB-Hackathon',100,912,890,46,29,{color:C.green,link:'https://github.com/uyqv/MongoDB-Hackathon'})
 ]}
];
export const deck={title:'Second Shift',width:1920,height:1080,colors:C,slides,targetSeconds:175,reserveSeconds:5,demoSeconds:90,demoFile:'media/second-shift-neuroai-90s.mp4'};
