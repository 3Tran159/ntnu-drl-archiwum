from pathlib import Path
R=Path(__file__).resolve().parent
p=R/'macros/BuildFlapPOC.java';s=p.read_text()
s=s.replace('if(!Paths.get(s.getSessionPath()).toAbsolutePath().normalize().equals(out.resolve("input_copy.sim").toAbsolutePath().normalize()))throw new IllegalStateException("Disposable POC copy required");','if(!"native_profile_poc_2606".equals(System.getenv("NTNU_FLAP_POC_BUILD"))||!s.getRegionManager().getRegions().isEmpty())throw new IllegalStateException("Owned empty POC simulation required");')
a=s.index('   note("clearing disposable copy");');b=s.index('   note("importing rounded native-profile parts");',a)
s=s[:a]+s[b:];p.write_text(s)
p=R/'launch_poc.py';s=p.read_text()
s=s.replace("macro=(R/'macros'/sys.argv[1]).resolve();sim=(R/sys.argv[2]).resolve()","macro=(R/'macros'/sys.argv[1]).resolve();new_case=sys.argv[2]=='NEW';sim=(R/sys.argv[2]).resolve()")
s=s.replace("and macro.exists() and sim.exists()","and macro.exists() and (new_case or sim.exists())")
s=s.replace("args.extend(['-np','1','-cpubind','off','-batch',str(macro),str(sim)])","args.extend(['-np','1','-cpubind','off']);args.extend(['-new'] if new_case else []);args.extend(['-batch',str(macro)]);args.extend([] if new_case else [str(sim)])")
s=s.replace("creationflags=subprocess.CREATE_NO_WINDOW)\nreceipt=", "creationflags=subprocess.CREATE_NO_WINDOW,env={**__import__('os').environ,'NTNU_FLAP_POC_BUILD':'native_profile_poc_2606'})\nreceipt=")
p.write_text(s)
print('Prepared isolated new POC from native geometry; original reference copy retained intact')
