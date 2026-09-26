import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath,pathToFileURL} from 'node:url';
import {createRequire} from 'node:module';
import {deck,C} from './content.mjs';
const here=path.dirname(fileURLToPath(import.meta.url));
const root=path.resolve(here,'../..'),out=path.resolve(here,'../delivery'),build=path.resolve(here,'../.build');
const require=createRequire(path.join(build,'runtime-loader.cjs'));
const {Presentation,PresentationFile}=await import(pathToFileURL(require.resolve('@oai/artifact-tool')));
const {GlobalFonts}=require('@napi-rs/canvas');
const fonts=path.join(out,'assets/fonts');
for(const font of await fs.readdir(fonts)){if(font.endsWith('.ttf'))GlobalFonts.registerFromPath(path.join(fonts,font));}
const artifactRequire=createRequire(require.resolve('@oai/artifact-tool'));
const {FontLibrary}=artifactRequire('skia-canvas');
for(const family of ['Space Grotesk','Source Sans 3']){const prefix=family.replaceAll(' ','');const list=(await fs.readdir(fonts)).filter(f=>f.startsWith(prefix)&&f.endsWith('.ttf')).map(f=>path.join(fonts,f));FontLibrary.use(family,list);}
const SKILL='/Users/andrewshatsky/.codex/plugins/cache/openai-primary-runtime/presentations/26.905.11957/skills/presentations';
const {finalizePresentation,applyPresentationChartFont}=await import(pathToFileURL(path.join(SKILL,'container_tools/artifact_tool_utils.mjs')));
const p=Presentation.create({slideSize:{width:1280,height:720}}),S=2/3, authoredSlides=[];
const pos=v=>({left:v.x*S,top:v.y*S,width:v.w*S,height:v.h*S});
function shape(s,v,geometry,fill='none',stroke='none',width=0){return s.shapes.add({geometry,position:pos(v),fill,line:{fill:stroke,width}})}
for(const d of deck.slides){
 const s=p.slides.add();authoredSlides.push(s);s.background.fill=C.bg;
 for(const v of d.elements){
  if(v.type==='text'){
   const t=shape(s,v,'textbox');
   const copy=d.id==='demo'&&v.text==='Press Enter to play'?'Play the accompanying demo MP4':v.text;
   t.text=v.link?[[{run:copy,link:{uri:v.link,isExternal:true}}]]:copy;
   t.text.style={typeface:v.font,fontSize:v.size*S,bold:v.weight>=600,color:v.color,alignment:v.align||'left',verticalAlignment:'top',wrap:'none',autoFit:'none',insets:{top:0,right:0,bottom:0,left:0}};
  }else if(v.type==='image'){
   const b=await fs.readFile(path.join(out,v.src));
   s.images.add({blob:b,contentType:v.src.endsWith('.svg')?'image/svg+xml':'image/png',alt:v.alt,fit:'contain',position:pos(v)});
  }else if(v.type==='line')shape(s,v,'line','none',v.color,0.7);
  else if(v.type==='memory')shape(s,v,'rect',C.pale,C.line,0.6);
  else if(v.type==='connector'){
   shape(s,{...v,y:v.y+8},'line','none',v.color,1.25);
   shape(s,{...v,x:v.x+v.w-12,y:v.y+2,w:12,h:12},'rightArrow',v.color);
  }else if(v.type==='chart'){
   const values=v.data.values,lo=Math.floor(Math.min(...values)/10)*10,hi=Math.ceil(Math.max(...values)/10)*10;
   const chart=s.charts.add('scatter',{
    position:pos(v),hasLegend:false,scatterOptions:{style:'line'},
    series:[{name:'C3 EEG (µV)',xValues:v.data.times,values,fill:C.green,line:{fill:C.green,width:1.3},marker:{symbol:'none'}}],
    xAxis:{visible:true,min:0,max:2,majorUnit:2,numberFormatCode:'0" s"',position:'bottom',textStyle:{fontFamily:'Source Sans 3',fontSize:15,fill:C.muted},majorGridlines:null,line:{fill:'none',width:0}},
    yAxis:{visible:true,min:lo,max:hi,majorUnit:(hi-lo)/2,numberFormatCode:'0',position:'left',textStyle:{fontFamily:'Source Sans 3',fontSize:15,fill:C.muted},majorGridlines:{fill:C.line,width:.6},line:{fill:'none',width:0}},
    chartFill:'none',plotAreaFill:'none',chartLine:{fill:'none',width:0},plotAreaLine:{fill:'none',width:0}
   });applyPresentationChartFont(chart,{fontFamily:'Source Sans 3'});
  }
 }
 // PPTX is the static backup. The browser owns motion and explicit video playback.
 s.speakerNotes.textFrame.setText(`${d.start}–${d.start+d.duration} seconds\n\n${d.notes}\n\nSources and context\n${d.sources.map(t=>'- '+t).join('\n')}${d.id==='demo'?'\n\nPlay the accompanying new 60-second MP4 from the media folder. Do not use previous demo recordings.':''}`);
}
const candidate=path.join(build,'candidate.pptx');
await(await PresentationFile.exportPptx(p)).save(candidate);
await fs.mkdir(path.join(build,'renders'),{recursive:true});
for(let i=0;i<deck.slides.length;i++){
 const slide=authoredSlides[i];
 const png=await p.export({slide,format:'png',scale:1.5});
 await fs.writeFile(path.join(build,'renders',`slide-${i+1}.png`),new Uint8Array(await png.arrayBuffer()));
 const layout=await slide.export({format:'layout'});await fs.writeFile(path.join(build,'renders',`slide-${i+1}.json`),await layout.text());
 console.log('Rendered slide',i+1);
}
const finalPath=path.join(out,process.argv[2]||'Second-Shift-Neuro-AI.pptx');
const result=await finalizePresentation({
 workspaceDir:root,candidatePath:candidate,finalPath,
 explicitTotalSlideCount:6,requiredNativeChartOwnerSlides:[2],requiredNativeTableOwnerSlides:[],materializeLiteralChartWorkbooks:true,
 pythonExecutable:'/Users/andrewshatsky/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3',
 integrityValidatorPath:path.join(SKILL,'container_tools/inspect_presentation_package_integrity.py'),
 layoutValidatorPath:path.join(SKILL,'container_tools/inspect_presentation_layout_geometry.py'),
 layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-heading-fit'],
 fontPolicy:{basis:'design',families:['Space Grotesk','Source Sans 3']},verifyArtifactToolImport:true,
 receiptPath:path.join(build,path.basename(finalPath)+'.validation.json')
});
console.log(JSON.stringify(result,null,2));
