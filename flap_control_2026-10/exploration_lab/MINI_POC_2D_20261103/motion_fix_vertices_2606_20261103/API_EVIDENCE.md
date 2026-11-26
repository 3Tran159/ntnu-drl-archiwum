# STAR2606 transient motion — verified API findings

Installed build2606.0002/21.04.009-R8. The priorphysics MeshDeformationModel was incompatible withImplicitUnsteadyModel. Correctpath isMotionManager.createMotion(MorphingMotion.class),assign toregionMotionSpecification;this activatesMorpherModel andMeshMorpher solver. True2Dcontinuum is preserved.

Native conditionintrospection confirmsmovingwalls,inletandoutlet exposeMorpherSpecification;Symmetryboundary exposesPlaneConstraintSpecification instead. Preserve itsnativeplanecondition rather thanrequesting amissingMorpherSpecification. This iswhy the firstcorrectMotion attemptstill failed.

UseTOTALdisplacementfromSavedCoord andMorphFromZero for closedcycles. RBFlinearfit,automaticthinout,correctorenabled;tolerance1e-9 ischosen fromSiemensguidanceforthinlayers. ALEgridflux isenabled. Physicalfields arecopied fromacceptedC0withoutreset;kinematiccopyfreezesCFD;URANS_STARTsavedbeforefreeze isseparate.

XYZtables require explicitvectorcomponents. SupplyingavectorfieldtoXYZproduced amagnitude,notthreecoordinates. Correctedtables exportPositioncomponentsplusnativeXYZwithvertexextractionactive. Verification comparesactualnativeXYZwiththeanalyticalcommandoninitialvertices. Topology/cellcount staysconstant;no remeshingorOverset.

Manufacturer sources installedwiththisexactversion:
- E:/Program Files/Siemens/21.04.009-R8/STAR-CCM+21.04.009-R8/doc/en/online/STARCCMP/GUID-02A980CD-9388-4AA1-A2D2-496A28D8BAE6.html — ActivatingtheMorpher
- E:/Program Files/Siemens/21.04.009-R8/STAR-CCM+21.04.009-R8/doc/en/online/STARCCMP/GUID-173022BA-03B2-4349-B5B0-172FB3057BB3.html — Boundaryproperties
- E:/Program Files/Siemens/21.04.009-R8/STAR-CCM+21.04.009-R8/doc/en/online/STARCCMP/GUID-7A38D378-8F67-4231-9B72-FFBCCF7E3EB2.html — MeshMorphersolver
- E:/Program Files/Siemens/21.04.009-R8/STAR-CCM+21.04.009-R8/doc/en/online/STARCCMP/GUID-5B66051D-B1F4-47A5-A48B-D5BC1DD9874B.html — SavedCoord(reference verified at runtime; local guidefieldfunctionswasGUID-5B66051D-B1F4-47A5-A48B-D5BC1DD9874B)

Previousstaticfiles andpriorHOLDresultsremainunchanged;newwhole-final25-residualgateisappliedtosmokeandreviewedseparatelyforstatic+2. Its0.399kPapressurereserveisalimitation,notaperiodicmotionvalidation.
