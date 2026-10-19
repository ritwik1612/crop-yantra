/* Original procedural rice model. No photographic billboards or image sprites.
 * Three.js r170 is vendored with its MIT license for fully offline rendering.
 */
import * as T from './assets/three.module.js';

export function createRiceScene(canvas){
 const renderer=new T.WebGLRenderer({canvas,alpha:true,antialias:true,powerPreference:'high-performance'});
 renderer.setPixelRatio(Math.min(devicePixelRatio||1,1.75));
 renderer.setClearColor(0x000000,0);renderer.outputColorSpace=T.SRGBColorSpace;
 renderer.toneMapping=T.ACESFilmicToneMapping;renderer.toneMappingExposure=1.12;
 const scene=new T.Scene(),camera=new T.PerspectiveCamera(36,1,.01,40),plant=new T.Group();
 plant.name='Paddy — connected procedural Oryza sativa';scene.add(plant);
 scene.add(new T.HemisphereLight(0xe2eccb,0x182616,.95));
 const key=new T.DirectionalLight(0xffedc7,3.6);key.position.set(-2,4,3);scene.add(key);
 const rim=new T.DirectionalLight(0xc9e4cb,2.5);rim.position.set(2,2,-2);scene.add(rim);
 const fill=new T.DirectionalLight(0xa0b77b,.7);fill.position.set(3,1,3);scene.add(fill);
 const inspectionLight=new T.DirectionalLight(0xf2f0de,0);scene.add(inspectionLight,inspectionLight.target);
 const {plant:rice,leaves,culms,heads,targets,diseaseIds,stemMat,branchMat}=buildRicePlant();plant.add(rice);
 new T.TextureLoader().load(new URL('./assets/rice-leaf-albedo.png',import.meta.url).href,texture=>{
  texture.colorSpace=T.SRGBColorSpace;texture.anisotropy=Math.min(8,renderer.capabilities.getMaxAnisotropy());
  leaves.forEach(leaf=>{leaf.material.color.set(0xd4d5ad).offsetHSL(0,0,Math.sin(leaf.phase)*.035);leaf.material.map=texture;leaf.material.bumpMap=texture;leaf.material.bumpScale=.0013;leaf.material.needsUpdate=true;});
 },undefined,()=>console.warn('Leaf surface texture unavailable; using procedural veins.'));
 const V=(x,y,z)=>new T.Vector3(x,y,z);
 let current='',viewCondition='';const look=V(0,1.2,0),eye=V(0,1.45,4.7),inspectionDirection=V(0,1,0);camera.position.copy(eye);
 const raycaster=new T.Raycaster();
 function clearView(leaf,anchor,preferred){
  let best=preferred.clone(),bestScore=-Infinity;
  // Test actual opaque scene occlusion only when selecting a leaf. No fading,
  // alpha masking or disconnected anatomy is used to manufacture visibility.
  for(const angle of [0,.35,-.35,.7,-.7,1.05,-1.05])for(const tilt of [0,.25]){
   const direction=preferred.clone().applyAxisAngle(V(0,1,0),angle).add(V(0,tilt,0)).normalize();if(direction.dot(preferred)<.3)continue;
   const origin=anchor.clone().addScaledVector(direction,.83),samples=[leaf.point(.52,0),leaf.point(.43,.2),leaf.point(.63,-.2)];let visible=0;
   for(const sample of samples){leaf.group.localToWorld(sample);raycaster.set(origin,sample.clone().sub(origin).normalize());const first=raycaster.intersectObject(plant,true)[0];if(first&&(first.object===leaf.mesh||first.object===leaf.rib))visible++;}
   const score=visible*10-Math.abs(angle)-tilt;if(score>bestScore){bestScore=score;best.copy(direction);}
  }
  return best;
 }
 const anchor=V(),normal=V(),desiredEye=V(),desiredLook=V(),up=V(0,1,0),q=new T.Quaternion(),axis=V();
 function resize(){const w=canvas.parentElement.clientWidth,h=canvas.parentElement.clientHeight;renderer.setSize(w,h,false);camera.aspect=w/Math.max(1,h);camera.updateProjectionMatrix();}
 const observer=new ResizeObserver(resize);observer.observe(canvas.parentElement);resize();
 function render(state){
  const {mode,condition,progress,time,wind,gust,yaw,pitch,zoom,paused,reduced,compare=true,focusLeaf,overview=false}=state;
  const selected=mode==='leaf'?condition:'normal',selectedLeaf=focusLeaf?.condition===selected?focusLeaf:targets[selected],severity=mode==='leaf'?progress:0;
  const comparing=mode==='leaf'&&compare&&selected!=='normal';
  if(current!==selected){current=selected;canvas.dataset.condition=selected;}
  culms.forEach((culm,i)=>{culm.rotation.z=paused||reduced?0:Math.sin(time*.85+i*.7)*wind*.007+gust*.027;culm.rotation.x=paused||reduced?0:Math.sin(time*.7+i)*wind*.003;});
  leaves.forEach(leaf=>{
   leaf.group.rotation.x=paused||reduced?0:Math.sin(time*1.3+leaf.phase)*wind*.012+gust*.025;
   const uniforms=leaf.material.userData.uniforms;
   const illustrated=comparing?leaf.condition:selected;
   const affected=comparing||selectedLeaf===leaf||(['blast','bacterial_leaf_streak','bacterial_blight','brown_spot','hispa','downy_mildew','tungro'].includes(selected)&&leaves.indexOf(leaf)%3!==0);
   uniforms.severity.value=affected?Math.pow(severity,.7)*(.78+.22*(.5+.5*Math.sin(leaf.phase))):0;uniforms.disease.value=diseaseIds[illustrated]||0;
   leaf.group.rotation.z=leaf.restZ+(illustrated==='dead_heart'&&affected?severity*.23:0);
   leaf.material.transparent=false;leaf.material.opacity=1;leaf.material.depthWrite=true;
   leaf.rib.material.transparent=false;leaf.rib.material.opacity=1;leaf.rib.material.depthWrite=true;
  });
  heads.forEach((head,i)=>{head.group.rotation.z=paused||reduced?0:Math.sin(time+i)*wind*.015;head.material.color.set(0xc1ae62);if(selected==='bacterial_panicle_blight'||comparing&&i===0)head.material.color.lerp(new T.Color(0x634226),severity);});
  for(const material of [stemMat,branchMat]){material.transparent=false;material.opacity=1;material.depthWrite=true;}
  heads.forEach(head=>{head.material.transparent=false;head.material.opacity=1;head.material.depthWrite=true;});
  plant.updateMatrixWorld(true);
  if(selectedLeaf&&!overview){
   const local=selectedLeaf.point(.52,0);anchor.copy(local);selectedLeaf.group.localToWorld(anchor);
   const tangent=selectedLeaf.point(.53,0).sub(selectedLeaf.point(.51,0)).normalize(),side=V(0,0,1);
   normal.crossVectors(side,tangent).normalize();if(normal.y<0)normal.negate();normal.transformDirection(selectedLeaf.group.matrixWorld);
   const viewKey=selected+selectedLeaf.phase;if(viewCondition!==viewKey){inspectionDirection.copy(clearView(selectedLeaf,anchor,normal));viewCondition=viewKey;}
   desiredLook.copy(anchor);desiredEye.copy(inspectionDirection).multiplyScalar(.83/zoom).add(anchor);
   // Orbit around the actual leaf normal, with genuine depth/parallax.
   axis.copy(desiredEye).sub(anchor);q.setFromAxisAngle(V(0,1,0),yaw);axis.applyQuaternion(q);
   q.setFromAxisAngle(V(1,0,0),pitch);axis.applyQuaternion(q);desiredEye.copy(anchor).add(axis);
   up.copy(tangent).transformDirection(selectedLeaf.group.matrixWorld);
  }else if(selected==='bacterial_panicle_blight'&&!overview){
   anchor.set(.15,.02,0);heads[0].group.localToWorld(anchor);desiredLook.copy(anchor);desiredEye.copy(anchor).add(V(Math.sin(yaw)*1.1,.48+pitch,Math.cos(yaw)*1.15).divideScalar(zoom));up.set(0,1,0);
  }else{viewCondition='';desiredLook.set(0,1.25,0);const distance=4.65/zoom;desiredEye.set(Math.sin(yaw)*distance,1.5+pitch*distance,Math.cos(yaw)*distance);up.set(0,1,0);}
  const ease=paused||reduced?1:.075;look.lerp(desiredLook,ease);eye.lerp(desiredEye,ease);camera.position.copy(eye);camera.up.lerp(up,ease).normalize();camera.lookAt(look);
  inspectionLight.intensity=selectedLeaf?2.1:0;inspectionLight.position.copy(eye);inspectionLight.target.position.copy(look);
  renderer.render(scene,camera);
 }
 let meshCount=0;plant.traverse(object=>{if(object.isMesh)meshCount++;});
 let grainCount=0;plant.traverse(object=>{if(object.isInstancedMesh)grainCount+=object.count;});
 canvas.dataset.renderer='webgl-3d';canvas.dataset.meshes=String(meshCount);canvas.dataset.grains=String(grainCount);
 canvas.addEventListener('webglcontextlost',event=>{event.preventDefault();canvas.dataset.renderer='context-lost';});
 function pickLeaf(clientX,clientY){const rect=canvas.getBoundingClientRect();raycaster.setFromCamera(new T.Vector2((clientX-rect.left)/rect.width*2-1,-(clientY-rect.top)/rect.height*2+1),camera);const hits=raycaster.intersectObject(plant,true);for(const hit of hits){const leaf=leaves.find(l=>l.mesh===hit.object);if(leaf)return leaf;}return null;}
 return {render,pickLeaf,dispose(){observer.disconnect();scene.traverse(object=>{object.geometry?.dispose();if(object.material)object.material.dispose();});renderer.dispose();},model:plant};
}

// Pure geometry builder: also used by the offline model-export/test tool.
export function buildRicePlant(){
 const plant=new T.Group();plant.name='Paddy — connected procedural Oryza sativa';
 const stemMat=new T.MeshStandardMaterial({color:0x657d2e,roughness:.51,metalness:0});
 const jointMat=new T.MeshStandardMaterial({color:0x96a25b,roughness:.65});
 const grainMat=new T.MeshStandardMaterial({color:0xc1ae62,roughness:.61});
 grainMat.onBeforeCompile=shader=>{
  shader.vertexShader='varying vec2 huskUV;\n'+shader.vertexShader.replace('#include <uv_vertex>','#include <uv_vertex>\nhuskUV=uv;');
  shader.fragmentShader='varying vec2 huskUV;\n'+shader.fragmentShader;
  shader.fragmentShader=shader.fragmentShader.replace('#include <color_fragment>','#include <color_fragment>\ndiffuseColor.rgb *= .88 + .1*cos(huskUV.x*100.) + .035*sin(huskUV.y*180. + huskUV.x*47.);');
 };
 const branchMat=new T.MeshStandardMaterial({color:0x89964b,roughness:.68});
 const leaves=[],culms=[],heads=[];
 const V=(x,y,z)=>new T.Vector3(x,y,z);
 function tube(points,radius,material,parent,segments=24){
  const curve=new T.CatmullRomCurve3(points),geometry=new T.TubeGeometry(curve,segments,radius,7,false);
  if(radius>.006){const positions=geometry.attributes.position,p=new T.Vector3();for(let i=0;i<=segments;i++){const centre=curve.getPointAt(i/segments),factor=1-i/segments*.55;for(let j=0;j<=7;j++){const k=i*8+j;p.fromBufferAttribute(positions,k).sub(centre).multiplyScalar(factor).add(centre);positions.setXYZ(k,p.x,p.y,p.z);}}geometry.computeVertexNormals();}
  const mesh=new T.Mesh(geometry,material);parent.add(mesh);return mesh;
 }
 function leafMaterial(seed){
  const material=new T.MeshPhysicalMaterial({color:0x557b39,roughness:.54,clearcoat:.10,clearcoatRoughness:.6,side:T.DoubleSide});
  material.color.offsetHSL(Math.sin(seed*3)*.012,Math.cos(seed)*.025,Math.sin(seed*1.7)*.025);
  const uniforms={severity:{value:0},disease:{value:0},seed:{value:seed}};
  material.onBeforeCompile=shader=>{
   Object.assign(shader.uniforms,uniforms);
   shader.vertexShader='varying vec2 leafUV;\n'+shader.vertexShader.replace('#include <uv_vertex>','#include <uv_vertex>\nleafUV=uv;');
   shader.fragmentShader='varying vec2 leafUV; uniform float severity; uniform float disease; uniform float seed;\n'+shader.fragmentShader;
   shader.fragmentShader=shader.fragmentShader.replace('#include <color_fragment>',`#include <color_fragment>
    vec2 q=leafUV;
    float veins=pow(.5+.5*cos(q.x*210.),14.);
    float rib=exp(-abs(q.x-.5)*95.);
    float variation=sin(q.y*230.+q.x*39.+seed)*sin(q.x*340.)*.018;
    diffuseColor.rgb*=.73+veins*.22+rib*.38+variation+sin(q.x*730.+sin(q.y*90.))*.035;
    float lesion=0.; float centre=0.;
    for(int i=0;i<14;i++){
     float n=float(i)+seed;
     vec2 p=vec2(.18+fract(sin(n*127.1)*43758.545)*.64,.13+fract(sin(n*311.7)*18371.3)*.76);
     vec2 d=(q-p)/(disease>3.5&&disease<4.5?vec2(.12,.012):vec2(.12,.04));
     float r=disease<1.5?abs(d.x)+abs(d.y):length(d);lesion=max(lesion,1.-smoothstep(.72,1.2,r));centre=max(centre,1.-smoothstep(.25,.62,r));
    }
    vec3 dead=vec3(.28,.13,.045);
    if(disease<1.5){dead=mix(dead,vec3(.63,.59,.43),centre);}
    else if(disease<2.5){lesion=smoothstep(.7,.95,abs(sin(q.x*87.+sin(q.y*15.)*.3)))*smoothstep(.15,.35,q.y);dead=vec3(.51,.32,.08);}
    else if(disease<3.5){lesion=smoothstep(.2,.49,abs(q.x-.5))+smoothstep(.63,1.,q.y);dead=vec3(.68,.52,.19);}
    else if(disease<4.5){dead=mix(vec3(.22,.09,.025),vec3(.47,.31,.12),centre);}
    else if(disease<5.5){lesion=0.;for(int j=0;j<4;j++){float n=float(j);float centreLine=.18+n*.205+sin(q.y*23.+n*2.)*.014;float scrape=1.-smoothstep(.018,.045,abs(q.x-centreLine));scrape*=smoothstep(.12+n*.05,.18+n*.05,q.y)*(1.-smoothstep(.76+n*.025,.83+n*.025,q.y));scrape*=smoothstep(.16,.32,fract(q.y*(4.+n*.43)+n*.37));lesion=max(lesion,scrape);}dead=vec3(.77,.76,.57);}
    else if(disease<6.5){lesion=.6+.3*sin(q.x*40.);dead=vec3(.64,.64,.23);}
    else if(disease<7.5){lesion=.88+.12*sin(q.x*71.+seed);dead=mix(vec3(.095,.036,.009),vec3(.26,.14,.045),veins);}
    else{lesion=.8;dead=vec3(.72,.48,.09);}
    diffuseColor.rgb=mix(diffuseColor.rgb,dead,clamp(lesion*severity,0.,.94));
   `);
  };
  material.customProgramCacheKey=()=> 'paddy-leaf-v1';material.userData.uniforms=uniforms;return material;
 }
 function addLeaf(parent,base,angle,length,width,seed){
  length*=.88+.19*(.5+.5*Math.sin(seed*7.23));width*=.82+.32*(.5+.5*Math.cos(seed*3.13));
  const group=new T.Group();group.position.copy(base);group.rotation.y=angle;parent.add(group);
  // A folded, tapered, twisted ribbon with real surface normals and depth.
  const geometry=new T.BufferGeometry(),positions=[],uvs=[],indices=[],along=60,across=12;
  function point(t,u){const breadth=width*Math.pow(Math.sin(Math.PI*t),.8)*(1-.34*t);
   return V(length*(.91*t+.14*t*t),length*(1.18*t-1.43*t*t)+Math.abs(u)*breadth*.27+Math.sin(u*28)*.0004*Math.sin(t*Math.PI),
    u*breadth+Math.sin(t*3.5+seed*.3)*length*.045+u*breadth*Math.sin(t*4.+seed)*.22);}
  for(let j=0;j<=along;j++)for(let i=0;i<=across;i++){
   const p=point(j/along,i/across*2-1);positions.push(...p.toArray());uvs.push(i/across,j/along);
  }
  for(let j=0;j<along;j++)for(let i=0;i<across;i++){const a=j*(across+1)+i,b=a+across+1;indices.push(a,b,a+1,b,b+1,a+1);}
  geometry.setAttribute('position',new T.Float32BufferAttribute(positions,3));geometry.setAttribute('uv',new T.Float32BufferAttribute(uvs,2));geometry.setIndex(indices);geometry.computeVertexNormals();
  const material=leafMaterial(seed),mesh=new T.Mesh(geometry,material);mesh.name='Attached leaf '+seed;group.add(mesh);
  // Explicit midrib, following the same centreline; no flat icon silhouette.
  const rib=tube(Array.from({length:18},(_,i)=>point(i/17,0)),.0014,jointMat.clone(),group,20);
  const data={group,mesh,material,point,rib,phase:seed*1.27};leaves.push(data);return data;
 }
 function addHead(parent,base,angle,seed){
  const group=new T.Group();group.position.copy(base);group.rotation.y=angle;parent.add(group);
  const spine=t=>V(.36*t,.25*Math.sin(t*Math.PI)-.38*t*t,.04*Math.sin(t*3));
  tube(Array.from({length:16},(_,i)=>spine(i/15)),.0036,branchMat,group);
  const grains=[],dummy=new T.Object3D();
  for(let j=0;j<12;j++){
   const t=.08+j*.073,root=spine(t),side=j%2?1:-1;
   const end=root.clone().add(V(.08+.09*Math.sin(t*Math.PI),-.08-.14*t,side*(.055+.10*Math.sin(t*Math.PI))));
   const control=root.clone().lerp(end,.45).add(V(.025,.035,0));
   const curve=new T.QuadraticBezierCurve3(root,control,end);
   tube(curve.getPoints(12),.0016,branchMat,group,14);
   for(let b=0;b<2;b++){
    const origin=curve.getPoint(.39+b*.3),tip=origin.clone().add(V(.035,-.045,side*(b%2?-.025:.032)));
    tube([origin,origin.clone().lerp(tip,.45).add(V(0,.007,0)),tip],.0008,branchMat,group,7);
    for(let g=0;g<3;g++)grains.push({p:origin.clone().lerp(tip,.36+g*.29),tangent:tip.clone().sub(origin).normalize(),scale:.74+.12*Math.sin(g+j)});
   }
   for(let k=0;k<8;k++){
    const s=.16+k*.105,p=curve.getPoint(s),tangent=curve.getTangent(s);
    p.z+=(k%2?1:-1)*.011;p.y-=.009;
    grains.push({p,tangent,scale:.83+.2*Math.sin(k*2+j+seed)});
   }
  }
  const profile=[new T.Vector2(0,-1.1),new T.Vector2(.38,-.9),new T.Vector2(.79,-.45),new T.Vector2(1,0),new T.Vector2(.83,.47),new T.Vector2(.43,.93),new T.Vector2(0,1.18)];
  const geo=new T.LatheGeometry(profile,12),grainMaterial=grainMat.clone();grainMaterial.onBeforeCompile=grainMat.onBeforeCompile;
  const instanced=new T.InstancedMesh(geo,grainMaterial,grains.length);
  grains.forEach(({p,tangent,scale},i)=>{dummy.position.copy(p);dummy.quaternion.setFromUnitVectors(V(0,1,0),tangent.clone().add(V(Math.sin(i*2)*.15,-.6,Math.cos(i)*.12)).normalize());dummy.scale.set(.007*scale*(1+Math.sin(i*3.1)*.12),.019*scale*(1+Math.cos(i*2.7)*.16),.0049*scale);dummy.updateMatrix();instanced.setMatrixAt(i,dummy.matrix);instanced.setColorAt(i,new T.Color().setHSL(.14+Math.sin(i*5+seed)*.018,.30,.71+Math.sin(i*2.3)*.09));});
  instanced.name='Individual rice grains';group.add(instanced);heads.push({group,material:grainMaterial});return group;
 }
 for(let n=0;n<4;n++){
  const culm=new T.Group(),height=[2.46,2.19,2.32,1.94][n],azimuth=n*2.4;
  culm.position.set(Math.cos(azimuth)*.09,0,Math.sin(azimuth)*.09);culm.rotation.y=azimuth*.24;plant.add(culm);culms.push(culm);
  const stemPoint=t=>V(.045*Math.sin(t*2+n),height*t,.025*Math.sin(t*3));
  tube(Array.from({length:20},(_,i)=>stemPoint(i/19)),.009-n*.0006,stemMat,culm);
  for(let j=1;j<6;j++){
   const node=stemPoint(j/6),ring=new T.Mesh(new T.TorusGeometry(.0105,.0018,5,10),jointMat);ring.rotation.x=Math.PI/2;ring.position.copy(node);culm.add(ring);
   addLeaf(culm,node,(j%2?0:Math.PI)+n*1.7+.22*j,.54+(6-j)*.12,.027+(6-j)*.003,n*7+j);
  }
  const flag=addLeaf(culm,stemPoint(.83),n*1.7+.5,.56,.023,n*7+6);flag.group.rotation.z=.2;
  addHead(culm,stemPoint(1),n*1.4,n);
 }
 const bySeed=seed=>leaves.find(l=>l.material.userData.uniforms.seed.value===seed);
 const targets={blast:bySeed(5),bacterial_leaf_streak:bySeed(12),bacterial_blight:bySeed(4),brown_spot:bySeed(2),hispa:bySeed(10),downy_mildew:bySeed(16),dead_heart:bySeed(6),tungro:bySeed(3)};
 const diseaseIds={blast:1,bacterial_leaf_streak:2,bacterial_blight:3,brown_spot:4,hispa:5,downy_mildew:6,dead_heart:7,tungro:8};
 const leafConditions=['blast','bacterial_leaf_streak','bacterial_blight','brown_spot','hispa','downy_mildew','tungro'];
 leaves.forEach((leaf,i)=>{leaf.condition=leafConditions[i%leafConditions.length];leaf.restZ=leaf.group.rotation.z;leaf.mesh.userData.condition=leaf.condition;});
 Object.entries(targets).forEach(([condition,leaf])=>{leaf.condition=condition;leaf.mesh.userData.condition=condition;});

 return {plant,leaves,culms,heads,targets,diseaseIds,stemMat,branchMat};
}
