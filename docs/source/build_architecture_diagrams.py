"""Simple model-name and data-flow diagrams for the public project README."""
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'docs/architecture'
OUT.mkdir(parents=True,exist_ok=True)
plt.rcParams.update({'font.family':'DejaVu Sans','svg.fonttype':'none'})

def figure(name,title,nodes,edges,note):
    fig,ax=plt.subplots(figsize=(12,9))
    fig.patch.set_facecolor('#FAFCF8');ax.set_xlim(0,12);ax.set_ylim(0,9);ax.axis('off')
    ax.text(6,8.6,title,ha='center',fontsize=20,fontweight='bold',color='#173E2B')
    positions={}
    for key,x,y,w,h,label,future in nodes:
        positions[key]=(x,y,w,h)
        ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=.025,rounding_size=.12',
            facecolor='#F1F2F6' if future else '#EAF3E5',edgecolor='#74877A',linewidth=1.2))
        ax.text(x+w/2,y+h/2,label,ha='center',va='center',fontsize=11.5,color='#173E2B',linespacing=1.5)
    for a,b in edges:
        x,y,w,h=positions[a];xx,yy,ww,hh=positions[b]
        ax.annotate('',xy=(xx+ww/2,yy+hh),xytext=(x+w/2,y),
            arrowprops=dict(arrowstyle='-|>',color='#456C50',lw=1.6,shrinkA=4,shrinkB=4))
    ax.text(6,.15,note,ha='center',fontsize=9,color='#526958')
    for ext in ('svg','png'):fig.savefig(OUT/(name+'.'+ext),dpi=170,bbox_inches='tight',pad_inches=.25)
    plt.close(fig)

figure('01_data_preprocessing','Data to model-ready inputs',[
 ('g',.2,7.4,3.5,.65,'Government crop statistics',False),
 ('b',4.25,7.4,3.5,.65,'GADM district data',False),
 ('w',8.3,7.4,3.5,.65,'NASA POWER weather',False),
 ('m',3,6.15,6,.7,'Merged rice dataset',False),
 ('s',3,4.9,6,.7,'Chronological train / validation / test split',False),
 ('p',3,3.65,6,.7,'SimpleImputer + StandardScaler',False),
 ('std',.5,2.15,5,.9,'Scaled numerical data\n+ OneHotEncoder categories',False),
 ('dae',6.5,2.15,5,.9,'Denoising Autoencoder (DAE)\n+ OneHotEncoder categories',False),
 ('so',.5,.85,5,.7,'Standard training inputs',False),
 ('do',6.5,.85,5,.7,'DAE training inputs',False)],
 [('g','m'),('b','m'),('w','m'),('m','s'),('s','p'),('p','std'),('p','dae'),('std','so'),('dae','do')],
 'Same observations and yield labels; two alternative input representations.')

figure('02_models_training','Training inputs to yield output',[
 ('s',.5,7.2,5,.8,'Standard preprocessed inputs',False),
 ('d',6.5,7.2,5,.8,'DAE preprocessed inputs',False),
 ('sm',.5,5.5,5,1.0,'MLP regressor\nor HistGradientBoostingRegressor',True),
 ('dm',6.5,5.5,5,1.0,'MLP regressor\nor HistGradientBoostingRegressor',True),
 ('y',3,3.8,6,.8,'Predicted rice yield',True),
 ('e',3,2.3,6,.8,'Compare with observed YIELD\nMAE / RMSE / R-squared',True),
 ('o',3,.8,6,.8,'Selected model\nRice yield in tonnes per hectare',True)],
 [('s','sm'),('d','dm'),('sm','y'),('dm','y'),('y','e'),('e','o')],
 'Four separate experiments. Grey stages are proposed; yield models are not yet trained.')

figure('03_application','User input to application output',[
 ('u',2,7.3,8,.8,'User input\nState / district / season / year / rice area',False),
 ('w',2,5.9,8,.8,'Location + weather data\nFeature construction',True),
 ('p',2,4.5,8,.8,'Saved SimpleImputer + StandardScaler\n+ OneHotEncoder',True),
 ('d',2,3.1,8,.8,'Denoising Autoencoder (DAE)\nOnly for the DAE input route',True),
 ('m',2,1.7,8,.8,'Selected MLP regressor\nor HistGradientBoostingRegressor',True),
 ('o',2,.55,8,.7,'Output: predicted rice yield (t/ha)',True)],
 [('u','w'),('w','p'),('p','d'),('d','m'),('m','o')],
 'Proposed inference flow. The current APP beta displays illustrative results only.')
print('Created three simple model-name and data-flow diagrams')
