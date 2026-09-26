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
 {id:'opening',title:'Second Shift',start:0,duration:15,notes:'We built Second Shift, an autonomous research assistant for brain signals. It runs EEG experiments and keeps the research moving, even when its agent crashes, loses context, or receives a new constraint.',sources:['README.md: What it does','Conceptual artwork generated with built-in image_gen. Electrode placement is illustrative, not a measured montage.'],elements:[
  ...shell(1,'MongoDB × Cerebral Valley'),
  image('assets/brain-hero-alpha.png',932,135,910,850,'Conceptual porcelain brain sculpture with green electrode contacts',{motion:'sculpture',fit:'contain'}),
  text('AUTONOMOUS NEUROSCIENCE RESEARCH',96,240,810,44,25,{color:C.green,weight:600}),
  head('Second',89,305,840,188,176),head('Shift',89,477,770,190,176),
  text('An autonomous research assistant\nfor brain signals.',98,710,770,138,49,{lineHeight:1.18}),
  text('Andrew Shatsky and David Shatsky',98,914,780,40,26,{color:C.muted}),
 ]},
 {id:'signals',title:'Finding patterns in brain signals',start:15,duration:20,notes:'EEG records electrical activity from the scalp. Our task is concrete: distinguish imagined fists from imagined feet. Second Shift searches 225 configurations of electrodes, frequency bands, time windows, and classifiers. Every experiment produces a measured result that the next decision can use.',sources:['harness/contracts.py: 225 effective configurations','harness/eeg.py: within-subject run 6 training, run 10 validation, run 14 sealed test','PhysioNet EEG Motor Movement/Imagery v1.0.0: https://physionet.org/content/eegmmidb/1.0.0/','Plot: S001R06.edf, channel C3, first T1 cue at 12.5 seconds, unfiltered 160 Hz samples. See source/eeg.json.'],elements:[
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
 {id:'mechanism',title:'How Second Shift researches',start:35,duration:25,notes:'The planner chooses the next configuration using recorded evidence. Numerical code trains and evaluates it. MongoDB Atlas stores the goal, experiments, and results. Each decision starts with a fresh evidence packet. Exact database reads supply measured results. Vector search retrieves research notes. A replacement worker can continue the same campaign.',sources:['harness/worker.py','harness/context.py: exact reads of best, leaders, laggards, recent results; semantic retrieval over notes','harness/store.py: deduplication, protocol identity, lease-fenced commits','harness/eeg.py: numerical evaluation'],elements:[
  ...shell(3,'The research loop'),head('How Second Shift\nresearches',96,155,1500,245,106),
  text('A fresh decision. A persistent research record.',98,419,1560,62,42,{color:C.muted}),
  head('01',100,543,230,100,71,{color:C.green,motion:'worker-step'}),head('02',702,543,230,100,71,{color:C.green}),head('03',1304,543,230,100,71,{color:C.green}),
  head('AI chooses',100,657,522,75,59,{motion:'worker-step'}),head('Code measures',702,657,540,75,59),head('Atlas remembers',1304,657,540,75,56),
  text('The next EEG experiment',100,754,516,55,33,{color:C.muted,motion:'worker-step'}),text('A reproducible numerical result',702,754,542,55,32,{color:C.muted}),text('Evidence for the next decision',1304,754,522,55,32,{color:C.muted}),
  {type:'connector',x:525,y:585,w:115,h:1,color:C.green},{type:'connector',x:1130,y:585,w:114,h:1,color:C.green},
  text('Worker resets → context rebuilt',100,820,900,36,26,{color:C.green,motion:'worker-reset-label'}),
  {type:'memory',x:100,y:868,w:1720,h:64},
  text('Completed research persists across worker restarts',120,880,1630,40,30,{align:'center',color:C.green,weight:600})
 ]},
 {id:'demo',title:'The working system',start:60,duration:60,notes:'Play the new, narrated 60-second dashboard demo. Do not speak over the recorded voiceover. At the end, advance to the measured-results slide. This slot intentionally contains no previous recording. The final demo must show the actual newly recorded actions.',sources:['New recording required. Previous recordings and raw frames are excluded at the user’s request.','Use the voiceover embedded in the user’s new finished demo. The separately generated Eric narration is an optional alternate and must not be layered over that soundtrack.'],elements:[
  ...shell(4,'60-second dashboard demo'),
  head('The working\nsystem',96,188,1600,270,125),
  text('A research campaign survives\na restart and a new electrode limit.',100,530,1340,145,51,{lineHeight:1.2}),
  {type:'video',x:0,y:0,w:1920,h:1080,src:'media/second-shift-demo.mp4'},
  text('Press Enter to play',100,837,1100,55,35,{color:C.green,weight:600}),
 ]},
 {id:'evidence',title:'Measured on real EEG',start:120,duration:30,notes:'Our reference campaign reached seventy-three point two percent balanced accuracy on a held-out test scored once. That used twenty-one electrodes across five participants and seventy-five test trials. Separately, all eight recovery checks and all five constraint-change checks passed. These are small, offline experiments. They demonstrate the research loop, not clinical performance or a real-time decoder.',sources:['README.md: camp_0f8981ee, 0.774 validation, 0.732 sealed test, 21 electrodes, 75 test trials, subjects 1–5','eval/checks.json: camp_51b0f538 recovery 8/8; camp_66e4900c constraint 5/5','Reference campaign and reliability checks are separate from the new demo campaign.'],elements:[
  ...shell(5,'Evidence from completed runs'),head('Measured on real EEG',96,154,1730,143,105),
  text('REFERENCE CAMPAIGN · 21 ELECTRODES',100,370,1000,44,27,{color:C.green,weight:600}),
  head('73.2%',87,434,1060,281,235,{color:C.green}),
  text('held-out balanced accuracy',100,739,1030,73,48),
  text('5 participants · 75 test trials · test scored once',100,842,1080,46,30,{color:C.muted}),
  line(1270,375,554),text('SEPARATE RELIABILITY CHECKS',1270,400,555,44,25,{color:C.muted,weight:600}),
  head('8 / 8',1264,480,520,125,102),text('Recovery checks passed',1270,621,552,54,33),
  head('5 / 5',1264,728,520,125,102),text('Goal-change checks passed',1270,861,550,54,33),
  text('Offline demonstration, not a clinical or real-time decoder',100,937,1430,34,23,{color:C.muted})
 ]},
 {id:'closing',title:'Research that keeps its progress',start:150,duration:25,notes:'The Neuro AI value is a research assistant that can test ideas on real brain signals and preserve what it learns. Researchers can inspect the evidence, change an electrode budget, and continue from completed work. We built Second Shift to give the next experiment a reliable starting point. Thank you.',sources:['README.md: project scope and team','Repository: https://github.com/uyqv/MongoDB-Hackathon','Conceptual brain and evidence-layer artwork generated with built-in image_gen.'],elements:[
  ...shell(6,'Second Shift'),
  image('assets/brain-memory-alpha.png',968,150,884,826,'Conceptual brain sculpture above persistent layers of experimental evidence',{motion:'sculpture',fit:'contain'}),
  head('Research that\nkeeps its\nprogress',96,211,970,360,107),
  text('Autonomous EEG experiments.\nEvidence that survives the restart.',100,631,900,133,42,{color:C.muted,lineHeight:1.2}),
  text('Andrew Shatsky and David Shatsky',100,842,850,51,31,{weight:600}),
  text('github.com/uyqv/MongoDB-Hackathon',100,912,890,46,29,{color:C.green,link:'https://github.com/uyqv/MongoDB-Hackathon'})
 ]}
];
export const deck={title:'Second Shift',width:1920,height:1080,colors:C,slides};
