"""ArtDef 片段模板：单位 / 成员 / 兵种三种 XML 文本。"""
def get_bins_template(bin,group,culture,assetname):
    return f"""<Element>
				<m_Fields>
					<m_Values/>
				</m_Fields>
				<m_ChildCollections>
					<Element>
						<m_CollectionName text="Groups"/>
						<m_ReplaceMergedCollectionElements>false</m_ReplaceMergedCollectionElements>
						<Element>
							<m_Fields>
								<m_Values/>
							</m_Fields>
							<m_ChildCollections>
								<Element>
									<m_CollectionName text="Cultures"/>
									<m_ReplaceMergedCollectionElements>false</m_ReplaceMergedCollectionElements>
									<Element>
										<m_Fields>
											<m_Values>
												<Element class="AssetObjects..ArtDefReferenceValue">
													<m_ElementName text=""/>
													<m_RootCollectionName text="UnitTintTypes"/>
													<m_ArtDefPath text=""/>
													<m_CollectionIsLocked>true</m_CollectionIsLocked>
													<m_TemplateName text=""/>
													<m_ParamName text="Tint"/>
												</Element>
											</m_Values>
										</m_Fields>
										<m_ChildCollections>
											<Element>
												<m_CollectionName text="Assets"/>
												<m_ReplaceMergedCollectionElements>false</m_ReplaceMergedCollectionElements>
												<Element>
													<m_Fields>
														<m_Values>
															<Element class="AssetObjects..BLPEntryValue">
																<m_EntryName text="{assetname}"/>
																<m_XLPClass text="Unit"/>
																<m_XLPPath text="units.xlp"/>
																<m_BLPPackage text="units/units"/>
																<m_LibraryName text="Unit"/>
																<m_ParamName text="Asset"/>
															</Element>
															<Element class="AssetObjects..FloatValue">
																<m_fValue>1.000000</m_fValue>
																<m_ParamName text="Scale"/>
															</Element>
														</m_Values>
													</m_Fields>
													<m_ChildCollections/>
													<m_Name text="asset1"/>
													<m_AppendMergedParameterCollections>false</m_AppendMergedParameterCollections>
												</Element>
											</Element>
										</m_ChildCollections>
										<m_Name text="{culture}"/>
										<m_AppendMergedParameterCollections>false</m_AppendMergedParameterCollections>
									</Element>
								</Element>
							</m_ChildCollections>
							<m_Name text="{group}"/>
							<m_AppendMergedParameterCollections>false</m_AppendMergedParameterCollections>
						</Element>
					</Element>
				</m_ChildCollections>
				<m_Name text="{bin}"/>
				<m_AppendMergedParameterCollections>false</m_AppendMergedParameterCollections>
			</Element>"""

def get_members_template(MemberType,BinPath):
    return f"""<Element>
				<m_Fields>
					<m_Values>
						<Element class="AssetObjects..ArtDefReferenceValue">
							<m_ElementName text="Warrior"/>
							<m_RootCollectionName text="UnitMovementTypes"/>
							<m_ArtDefPath text="Units.artdef"/>
							<m_CollectionIsLocked>true</m_CollectionIsLocked>
							<m_TemplateName text="Units"/>
							<m_ParamName text="Movement"/>
						</Element>
						<Element class="AssetObjects..ArtDefReferenceValue">
							<m_ElementName text="WarriorCombat"/>
							<m_RootCollectionName text="MemberCombat"/>
							<m_ArtDefPath text="Units.artdef"/>
							<m_CollectionIsLocked>true</m_CollectionIsLocked>
							<m_TemplateName text="Units"/>
							<m_ParamName text="Combat"/>
						</Element>
						<Element class="AssetObjects..ArtDefReferenceValue">
							<m_ElementName text="DEFAULT"/>
							<m_RootCollectionName text="MaterialTypes"/>
							<m_ArtDefPath text="VFX.artdef"/>
							<m_CollectionIsLocked>true</m_CollectionIsLocked>
							<m_TemplateName text="VFX"/>
							<m_ParamName text="VFXMaterialType"/>
						</Element>
						<Element class="AssetObjects..ArtDefReferenceValue">
							<m_ElementName text="DEFAULT"/>
							<m_RootCollectionName text="MaterialTypes"/>
							<m_ArtDefPath text="VFX.artdef"/>
							<m_CollectionIsLocked>true</m_CollectionIsLocked>
							<m_TemplateName text="VFX"/>
							<m_ParamName text="VFXWeaponImpact"/>
						</Element>
						<Element class="AssetObjects..FloatValue">
							<m_fValue>0.000000</m_fValue>
							<m_ParamName text="ImpactHeightOverride"/>
						</Element>
					</m_Values>
				</m_Fields>
				<m_ChildCollections>
					<Element>
						<m_CollectionName text="Cultures"/>
						<m_ReplaceMergedCollectionElements>false</m_ReplaceMergedCollectionElements>
						<Element>
							<m_Fields>
								<m_Values/>
							</m_Fields>
							<m_ChildCollections>
								<Element>
									<m_CollectionName text="Variations"/>
									<m_ReplaceMergedCollectionElements>false</m_ReplaceMergedCollectionElements>
									<Element>
										<m_Fields>
											<m_Values>
												<Element class="AssetObjects..FloatValue">
													<m_fValue>1.000000</m_fValue>
													<m_ParamName text="Scale"/>
												</Element>
												<Element class="AssetObjects..BoolValue">
													<m_bValue>false</m_bValue>
													<m_ParamName text="IsAttachment"/>
												</Element>
											</m_Values>
										</m_Fields>
										<m_ChildCollections>
											<Element>
												<m_CollectionName text="Attachments"/>
												<m_ReplaceMergedCollectionElements>false</m_ReplaceMergedCollectionElements>
												<Element>
													<m_Fields>
														<m_Values>
															<Element class="AssetObjects..StringValue">
																<m_Value text="Root"/>
																<m_ParamName text="Point"/>
															</Element>
															<Element class="AssetObjects..ArtDefReferenceValue">
																<m_ElementName text=""/>
																<m_RootCollectionName text="UnitTintTypes"/>
																<m_ArtDefPath text=""/>
																<m_CollectionIsLocked>true</m_CollectionIsLocked>
																<m_TemplateName text=""/>
																<m_ParamName text="Tint"/>
															</Element>
														</m_Values>
													</m_Fields>
													<m_ChildCollections>
														<Element>
															<m_CollectionName text="Bins"/>
															<m_ReplaceMergedCollectionElements>false</m_ReplaceMergedCollectionElements>
															<Element>
																<m_Fields>
																	<m_Values/>
																</m_Fields>
																<m_ChildCollections/>
																<m_Name text="{BinPath}"/>
																<m_AppendMergedParameterCollections>false</m_AppendMergedParameterCollections>
															</Element>
														</Element>
													</m_ChildCollections>
													<m_Name text="Body"/>
													<m_AppendMergedParameterCollections>false</m_AppendMergedParameterCollections>
												</Element>
											</Element>
										</m_ChildCollections>
										<m_Name text="A"/>
										<m_AppendMergedParameterCollections>false</m_AppendMergedParameterCollections>
									</Element>
								</Element>
							</m_ChildCollections>
							<m_Name text="Any"/>
							<m_AppendMergedParameterCollections>false</m_AppendMergedParameterCollections>
						</Element>
					</Element>
				</m_ChildCollections>
				<m_Name text="{MemberType}"/>
				<m_AppendMergedParameterCollections>false</m_AppendMergedParameterCollections>
			</Element>"""

def get_units_template(UnitType,MemberType):
    return f"""<Element>
				<m_Fields>
					<m_Values>
						<Element class="AssetObjects..ArtDefReferenceValue">
							<m_ElementName text="Warrior"/>
							<m_RootCollectionName text="UnitFormationTypes"/>
							<m_ArtDefPath text="Units.artdef"/>
							<m_CollectionIsLocked>true</m_CollectionIsLocked>
							<m_TemplateName text="Units"/>
							<m_ParamName text="Formation"/>
						</Element>
						<Element class="AssetObjects..ArtDefReferenceValue">
							<m_ElementName text="Warrior"/>
							<m_RootCollectionName text="UnitCombat"/>
							<m_ArtDefPath text="Units.artdef"/>
							<m_CollectionIsLocked>true</m_CollectionIsLocked>
							<m_TemplateName text="Units"/>
							<m_ParamName text="UnitCombat"/>
						</Element>
						<Element class="AssetObjects..ArtDefReferenceValue">
							<m_ElementName text="Warrior"/>
							<m_RootCollectionName text="UnitFormationTypes"/>
							<m_ArtDefPath text="Units.artdef"/>
							<m_CollectionIsLocked>true</m_CollectionIsLocked>
							<m_TemplateName text="Units"/>
							<m_ParamName text="EscortFormation"/>
						</Element>
						<Element class="AssetObjects..ArtDefReferenceValue">
							<m_ElementName text=""/>
							<m_RootCollectionName text="Units"/>
							<m_ArtDefPath text="Units.artdef"/>
							<m_CollectionIsLocked>true</m_CollectionIsLocked>
							<m_TemplateName text=""/>
							<m_ParamName text="EmbarkedUnit"/>
						</Element>
						<Element class="AssetObjects..BoolValue">
							<m_bValue>false</m_bValue>
							<m_ParamName text="DoNotDisplayCharges"/>
						</Element>
						<Element class="AssetObjects..ArtDefReferenceValue">
							<m_ElementName text=""/>
							<m_RootCollectionName text="UnitCulture"/>
							<m_ArtDefPath text="Cultures.artdef"/>
							<m_CollectionIsLocked>true</m_CollectionIsLocked>
							<m_TemplateName text=""/>
							<m_ParamName text="Culture"/>
						</Element>
						<Element class="AssetObjects..ArtDefReferenceValue">
							<m_ElementName text=""/>
							<m_RootCollectionName text="Era"/>
							<m_ArtDefPath text="Eras.artdef"/>
							<m_CollectionIsLocked>true</m_CollectionIsLocked>
							<m_TemplateName text=""/>
							<m_ParamName text="Era"/>
						</Element>
						<Element class="AssetObjects..ArtDefReferenceValue">
							<m_ElementName text=""/>
							<m_RootCollectionName text="Units"/>
							<m_ArtDefPath text="Units.artdef"/>
							<m_CollectionIsLocked>true</m_CollectionIsLocked>
							<m_TemplateName text=""/>
							<m_ParamName text="ProxyUnit"/>
						</Element>
						<Element class="AssetObjects..BoolValue">
							<m_bValue>false</m_bValue>
							<m_ParamName text="PlayDeathOnDestroy"/>
						</Element>
						<Element class="AssetObjects..IntValue">
							<m_nValue>0</m_nValue>
							<m_ParamName text="DisplayLevel"/>
						</Element>
					</m_Values>
				</m_Fields>
				<m_ChildCollections>
					<Element>
						<m_CollectionName text="Members"/>
						<m_ReplaceMergedCollectionElements>false</m_ReplaceMergedCollectionElements>
						<Element>
							<m_Fields>
								<m_Values>
									<Element class="AssetObjects..FloatValue">
										<m_fValue>1.000000</m_fValue>
										<m_ParamName text="Scale"/>
									</Element>
									<Element class="AssetObjects..IntValue">
										<m_nValue>1</m_nValue>
										<m_ParamName text="Count"/>
									</Element>
									<Element class="AssetObjects..ArtDefReferenceValue">
										<m_ElementName text="{MemberType}"/>
										<m_RootCollectionName text="UnitMemberTypes"/>
										<m_ArtDefPath text="Units.artdef"/>
										<m_CollectionIsLocked>true</m_CollectionIsLocked>
										<m_TemplateName text="Units"/>
										<m_ParamName text="Type"/>
									</Element>
								</m_Values>
							</m_Fields>
							<m_ChildCollections/>
							<m_Name text="Member1"/>
							<m_AppendMergedParameterCollections>false</m_AppendMergedParameterCollections>
						</Element>
					</Element>
					<Element>
						<m_CollectionName text="Audio"/>
						<m_ReplaceMergedCollectionElements>false</m_ReplaceMergedCollectionElements>
					</Element>
					<Element>
						<m_CollectionName text="AttachmentVisibility"/>
						<m_ReplaceMergedCollectionElements>false</m_ReplaceMergedCollectionElements>
					</Element>
				</m_ChildCollections>
				<m_Name text="{UnitType}"/>
				<m_AppendMergedParameterCollections>false</m_AppendMergedParameterCollections>
			</Element>"""
