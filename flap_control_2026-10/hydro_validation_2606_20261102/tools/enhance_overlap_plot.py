from pathlib import Path
h=Path(__file__).resolve().parents[1];p=h/'tools/plot_overlap_mesh.py';s=p.read_text(encoding='utf8')
s=s.replace("axs[0,j].set_title(title,fontsize=12)","bad=near[near['Overset Interpolation Type'].between(4,6)]\n axs[0,j].scatter(bad['X (m)'],bad['Z (m)'],marker='x',s=70,c='black',linewidths=2,zorder=10)\n axs[0,j].set_title(('Kontrola' if j==0 else 'Lokalna poprawka')+' — '+str(len(f))+' komórek\\nTrudne stencile w widoku: '+str(len(bad)),fontsize=11)")
p.write_text(s,encoding='utf8')
print('Plot uses actual cell counts and highlights difficult stencils.')
