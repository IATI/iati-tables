<?xml version="1.0" encoding="UTF-8"?>

<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
    <xsl:output indent="yes"/>
    <xsl:template match="iati-activities">
        <iati-activities version="2.03">
            <xsl:if test="@generated-datetime"><xsl:attribute name="generated-datetime"><xsl:value-of select="@generated-datetime" /></xsl:attribute></xsl:if>
            <xsl:if test="@linked-data-default"><xsl:attribute name="linked-data-default"><xsl:value-of select="@linked-data-default" /></xsl:attribute></xsl:if>

            <xsl:for-each select="iati-activity">
                <iati-activity>
                    <xsl:if test="@last-updated-datetime"><xsl:attribute name="last-updated-datetime"><xsl:value-of select="@last-updated-datetime" /></xsl:attribute></xsl:if>
                    <xsl:if test="@xml:lang"><xsl:attribute name="xml:lang"><xsl:value-of select="@xml:lang" /></xsl:attribute></xsl:if>
                    <xsl:if test="default-currency"><xsl:attribute name="default-currency"><xsl:value-of select="default-currency" /></xsl:attribute></xsl:if>
                    <xsl:if test="@hierarchy"><xsl:attribute name="hierarchy"><xsl:value-of select="@hierarchy" /></xsl:attribute></xsl:if>
                    <xsl:if test="@linked-data-uri"><xsl:attribute name="linked-data-uri"><xsl:value-of select="@linked-data-uri" /></xsl:attribute></xsl:if>

                    <xsl:for-each select="iati-identifier">
                        <iati-identifier>
                            <xsl:value-of select="text()" />
                        </iati-identifier>
                    </xsl:for-each>

                    <xsl:if test="reporting-org">
                        <reporting-org>
                            <xsl:if test="reporting-org/@ref"><xsl:attribute name="ref"><xsl:value-of select="reporting-org/@ref" /></xsl:attribute></xsl:if>
                            <xsl:if test="reporting-org/@type"><xsl:attribute name="type"><xsl:value-of select="reporting-org/@type" /></xsl:attribute></xsl:if>
                            <xsl:if test="reporting-org/@secondary-reporter"><xsl:attribute name="secondary-reporter"><xsl:value-of select="reporting-org/@secondary-reporter" /></xsl:attribute></xsl:if>

                            <xsl:for-each select="reporting-org">
                                <narrative>
                                    <xsl:if test="@xml:lang"><xsl:attribute name="xml:lang"><xsl:value-of select="@xml:lang" /></xsl:attribute></xsl:if>
                                    <xsl:value-of select="text()" />
                                </narrative>
                            </xsl:for-each>
                        </reporting-org>
                    </xsl:if>

                    <xsl:if test="title">
                        <title>
                            <xsl:for-each select="title">
                                <narrative>
                                    <xsl:if test="@xml:lang"><xsl:attribute name="xml:lang"><xsl:value-of select="@xml:lang" /></xsl:attribute></xsl:if>
                                    <xsl:value-of select="text()" />
                                </narrative>
                            </xsl:for-each>
                        </title>
                    </xsl:if>

                    <xsl:if test="description">
                        <description>
                            <xsl:if test="description/@type"><xsl:attribute name="type"><xsl:value-of select="description/@type" /></xsl:attribute></xsl:if>
                            <xsl:for-each select="description">
                                <narrative>
                                    <xsl:if test="@xml:lang"><xsl:attribute name="xml:lang"><xsl:value-of select="@xml:lang" /></xsl:attribute></xsl:if>
                                    <xsl:value-of select="text()" />
                                </narrative>
                            </xsl:for-each>
                        </description>
                    </xsl:if>

                    <xsl:for-each select="participating-org">
                        <participating-org>
                            <xsl:if test="@ref"><xsl:attribute name="ref"><xsl:value-of select="@ref" /></xsl:attribute></xsl:if>
                            <xsl:if test="@type"><xsl:attribute name="type"><xsl:value-of select="@type" /></xsl:attribute></xsl:if>
                            <xsl:if test="@role = 'Funding'"><xsl:attribute name="role">1</xsl:attribute></xsl:if>
                            <xsl:if test="@role = 'Accountable'"><xsl:attribute name="role">2</xsl:attribute></xsl:if>
                            <xsl:if test="@role = 'Extending'"><xsl:attribute name="role">3</xsl:attribute></xsl:if>
                            <xsl:if test="@role = 'Implementing'"><xsl:attribute name="role">4</xsl:attribute></xsl:if>
                                <narrative>
                                    <xsl:if test="@xml:lang"><xsl:attribute name="xml:lang"><xsl:value-of select="@xml:lang" /></xsl:attribute></xsl:if>
                                    <xsl:value-of select="text()" />
                                </narrative>
                        </participating-org>
                    </xsl:for-each>

                    <xsl:if test="other-identifier">
                        <other-identifier type="A9">
                            <xsl:attribute name="ref"><xsl:value-of select="other-identifier/text()" /></xsl:attribute>
                            <owner-org>
                                <xsl:if test="other-identifier/@owner-ref"><xsl:attribute name="ref"><xsl:value-of select="other-identifier/@owner-ref" /></xsl:attribute></xsl:if>
                                <narrative>
                                    <xsl:value-of select="other-identifier/@owner-name" />
                                </narrative>
                            </owner-org>
                        </other-identifier>
                    </xsl:if>

                    <xsl:if test="activity-status">
                        <activity-status>
                            <xsl:if test="activity-status/@code"><xsl:attribute name="code"><xsl:value-of select="activity-status/@code" /></xsl:attribute></xsl:if>
                        </activity-status>
                    </xsl:if>

                    <xsl:for-each select="activity-date">
                        <activity-date>
                            <xsl:if test="@iso-date"><xsl:attribute name="iso-date"><xsl:value-of select="@iso-date" /></xsl:attribute></xsl:if>
                            <xsl:if test="@type = 'start-planned'"><xsl:attribute name="type">1</xsl:attribute></xsl:if>
                            <xsl:if test="@type = 'start-actual'"><xsl:attribute name="type">2</xsl:attribute></xsl:if>
                            <xsl:if test="@type = 'end-planned'"><xsl:attribute name="type">3</xsl:attribute></xsl:if>
                            <xsl:if test="@type = 'end-actual'"><xsl:attribute name="type">4</xsl:attribute></xsl:if>

                            <narrative>
                                <xsl:if test="@xml:lang"><xsl:attribute name="xml:lang"><xsl:value-of select="@xml:lang" /></xsl:attribute></xsl:if>
                                <xsl:value-of select="text()" />
                            </narrative>
                        </activity-date>
                    </xsl:for-each>

                    <xsl:for-each select="contact-info">
                        <contact-info>
                            <xsl:if test="@type"><xsl:attribute name="type"><xsl:value-of select="@type" /></xsl:attribute></xsl:if>

                            <xsl:if test="organisation">
                                <organisation>
                                    <xsl:for-each select="organisation">
                                        <narrative>
                                            <xsl:if test="@xml:lang"><xsl:attribute name="xml:lang"><xsl:value-of select="@xml:lang" /></xsl:attribute></xsl:if>
                                            <xsl:value-of select="text()" />
                                        </narrative>
                                    </xsl:for-each>
                                </organisation>
                            </xsl:if>
                            <xsl:if test="person-name">
                                <person-name>
                                    <xsl:for-each select="person-name">
                                        <narrative>
                                            <xsl:if test="@xml:lang"><xsl:attribute name="xml:lang"><xsl:value-of select="@xml:lang" /></xsl:attribute></xsl:if>
                                            <xsl:value-of select="text()" />
                                        </narrative>
                                    </xsl:for-each>
                                </person-name>
                            </xsl:if>
                            <xsl:if test="job-title">
                                <job-title>
                                    <xsl:for-each select="job-title">
                                        <narrative>
                                            <xsl:if test="@xml:lang"><xsl:attribute name="xml:lang"><xsl:value-of select="@xml:lang" /></xsl:attribute></xsl:if>
                                            <xsl:value-of select="text()" />
                                        </narrative>
                                    </xsl:for-each>
                                </job-title>
                            </xsl:if>
                            <xsl:if test="telephone">
                                <telephone>
                                    <xsl:value-of select="telephone/text()" />
                                </telephone>
                            </xsl:if>
                            <xsl:if test="email">
                                <email>
                                    <xsl:value-of select="email/text()" />
                                </email>
                            </xsl:if>
                            <xsl:if test="website">
                                <website>
                                    <xsl:value-of select="website/text()" />
                                </website>
                            </xsl:if>
                            <xsl:if test="mailing-address">
                                <mailing-address>
                                    <xsl:for-each select="mailing-address">
                                        <narrative>
                                            <xsl:if test="@xml:lang"><xsl:attribute name="xml:lang"><xsl:value-of select="@xml:lang" /></xsl:attribute></xsl:if>
                                            <xsl:value-of select="text()" />
                                        </narrative>
                                    </xsl:for-each>
                                </mailing-address>
                            </xsl:if>
                        </contact-info>
                    </xsl:for-each>

                    <xsl:if test="activity-scope">
                        <activity-scope>
                            <xsl:if test="activity-scope/@code"><xsl:attribute name="code"><xsl:value-of select="activity-scope/@code" /></xsl:attribute></xsl:if>
                        </activity-scope>
                    </xsl:if>

                    <xsl:for-each select="recipient-country">
                        <recipient-country>
                            <xsl:if test="@code"><xsl:attribute name="code"><xsl:value-of select="@code" /></xsl:attribute></xsl:if>
                            <xsl:if test="@percentage"><xsl:attribute name="percentage"><xsl:value-of select="@percentage" /></xsl:attribute></xsl:if>
                            <narrative>
                                <xsl:if test="@xml:lang"><xsl:attribute name="xml:lang"><xsl:value-of select="@xml:lang" /></xsl:attribute></xsl:if>
                                <xsl:value-of select="text()" />
                            </narrative>
                        </recipient-country>
                    </xsl:for-each>

                    <xsl:for-each select="recipient-region">
                        <recipient-region>
                            <xsl:if test="@code"><xsl:attribute name="code"><xsl:value-of select="@code" /></xsl:attribute></xsl:if>
                            <xsl:if test="@vocabulary"><xsl:attribute name="vocabulary"><xsl:value-of select="@vocabulary" /></xsl:attribute></xsl:if>
                            <xsl:if test="@percentage"><xsl:attribute name="percentage"><xsl:value-of select="@percentage" /></xsl:attribute></xsl:if>
                            <narrative>
                                <xsl:if test="@xml:lang"><xsl:attribute name="xml:lang"><xsl:value-of select="@xml:lang" /></xsl:attribute></xsl:if>
                                <xsl:value-of select="text()" />
                            </narrative>
                        </recipient-region>
                    </xsl:for-each>

                    <xsl:for-each select="location">
                        <location>
                            <xsl:if test="@ref"><xsl:attribute name="ref"><xsl:value-of select="@ref" /></xsl:attribute></xsl:if>

                            <xsl:if test="location-reach">
                                <location-reach>
                                    <xsl:if test="location-reach/@code"><xsl:attribute name="code"><xsl:value-of select="location-reach/@code" /></xsl:attribute></xsl:if>
                                </location-reach>
                            </xsl:if>
                            <xsl:if test="location-id">
                                <location-id>
                                    <xsl:if test="location-id/@code"><xsl:attribute name="code"><xsl:value-of select="location-id/@code" /></xsl:attribute></xsl:if>
                                    <xsl:if test="location-id/@vocabulary"><xsl:attribute name="vocabulary"><xsl:value-of select="location-id/@vocabulary" /></xsl:attribute></xsl:if>
                                </location-id>
                            </xsl:if>

                            <xsl:if test="name">
                                <name>
                                    <xsl:for-each select="name">
                                        <narrative>
                                            <xsl:if test="@xml:lang"><xsl:attribute name="xml:lang"><xsl:value-of select="@xml:lang" /></xsl:attribute></xsl:if>
                                            <xsl:value-of select="text()" />
                                        </narrative>
                                    </xsl:for-each>
                                </name>
                            </xsl:if>

                            <xsl:if test="description">
                                <description>
                                    <xsl:for-each select="description">
                                        <narrative>
                                            <xsl:if test="@xml:lang"><xsl:attribute name="xml:lang"><xsl:value-of select="@xml:lang" /></xsl:attribute></xsl:if>
                                            <xsl:value-of select="text()" />
                                        </narrative>
                                    </xsl:for-each>
                                </description>
                            </xsl:if>

                            <xsl:if test="activity-description">
                                <activity-description>
                                    <xsl:for-each select="activity-description">
                                        <narrative>
                                            <xsl:if test="@xml:lang"><xsl:attribute name="xml:lang"><xsl:value-of select="@xml:lang" /></xsl:attribute></xsl:if>
                                            <xsl:value-of select="text()" />
                                        </narrative>
                                    </xsl:for-each>
                                </activity-description>
                            </xsl:if>

                            <xsl:if test="administrative and administrative/@code">
                                <administrative>
                                    <xsl:for-each select="administrative">
                                        <xsl:if test="@code"><xsl:attribute name="code"><xsl:value-of select="@code" /></xsl:attribute></xsl:if>
                                        <xsl:if test="@vocabulary"><xsl:attribute name="vocabulary"><xsl:value-of select="@vocabulary" /></xsl:attribute></xsl:if>
                                        <xsl:if test="@level"><xsl:attribute name="level"><xsl:value-of select="@level" /></xsl:attribute></xsl:if>
                                    </xsl:for-each>
                                </administrative>
                            </xsl:if>

                            <xsl:if test="point">
                                <point>
                                    <xsl:for-each select="point">
                                        <xsl:if test="@srsName"><xsl:attribute name="srsName"><xsl:value-of select="@srsName" /></xsl:attribute></xsl:if>
                                        <pos>
                                            <xsl:value-of select="pos/text()" />
                                        </pos>
                                    </xsl:for-each>
                                </point>
                            </xsl:if>
                            <xsl:if test="not(point) and coordinates">
                                <point srsName="http://www.opengis.net/def/crs/EPSG/0/4326">
                                    <xsl:for-each select="coordinates">
                                        <pos>
                                            <xsl:value-of select="@latitude" /> <xsl:value-of select="@longitude" />
                                        </pos>
                                    </xsl:for-each>
                                </point>
                            </xsl:if>

                            <xsl:if test="exactness">
                                <exactness>
                                    <xsl:if test="exactness/@code"><xsl:attribute name="code"><xsl:value-of select="exactness/@code" /></xsl:attribute></xsl:if>
                                </exactness>
                            </xsl:if>

                            <xsl:if test="location-class">
                                <location-class>
                                    <xsl:if test="location-class/@code"><xsl:attribute name="code"><xsl:value-of select="location-class/@code" /></xsl:attribute></xsl:if>
                                </location-class>
                            </xsl:if>

                            <xsl:if test="feature-designation">
                                <feature-designation>
                                    <xsl:if test="feature-designation/@code"><xsl:attribute name="code"><xsl:value-of select="feature-designation/@code" /></xsl:attribute></xsl:if>
                                </feature-designation>
                            </xsl:if>
                        </location>
                    </xsl:for-each>

                    <xsl:for-each select="sector">
                        <sector>
                            <xsl:if test="@code"><xsl:attribute name="code"><xsl:value-of select="@code" /></xsl:attribute></xsl:if>
                            <xsl:if test="@vocabulary = 'DAC'"><xsl:attribute name="vocabulary">1</xsl:attribute></xsl:if>
                            <xsl:if test="@vocabulary = 'DAC-3'"><xsl:attribute name="vocabulary">2</xsl:attribute></xsl:if>
                            <xsl:if test="@vocabulary = 'COFOG'"><xsl:attribute name="vocabulary">3</xsl:attribute></xsl:if>
                            <xsl:if test="@vocabulary = 'NACE'"><xsl:attribute name="vocabulary">4</xsl:attribute></xsl:if>
                            <xsl:if test="@vocabulary = 'NTEE'"><xsl:attribute name="vocabulary">5</xsl:attribute></xsl:if>
                            <xsl:if test="@vocabulary = 'ADT'"><xsl:attribute name="vocabulary">6</xsl:attribute></xsl:if>
                            <xsl:if test="@vocabulary = 'RO2'"><xsl:attribute name="vocabulary">98</xsl:attribute></xsl:if>
                            <xsl:if test="@vocabulary = 'RO'"><xsl:attribute name="vocabulary">99</xsl:attribute></xsl:if>
                            <xsl:if test="@percentage"><xsl:attribute name="percentage"><xsl:value-of select="@percentage" /></xsl:attribute></xsl:if>
                            <narrative>
                                <xsl:if test="@xml:lang"><xsl:attribute name="xml:lang"><xsl:value-of select="@xml:lang" /></xsl:attribute></xsl:if>
                                <xsl:value-of select="text()" />
                            </narrative>
                        </sector>
                    </xsl:for-each>

                    <xsl:if test="country-budget-items">
                        <country-budget-items>
                            <xsl:if test="country-budget-items/@vocabulary"><xsl:attribute name="vocabulary"><xsl:value-of select="country-budget-items/@vocabulary" /></xsl:attribute></xsl:if>
                            <xsl:for-each select="country-budget-items/budget-item">
                                <budget-item>
                                    <xsl:if test="@code"><xsl:attribute name="code"><xsl:value-of select="@code" /></xsl:attribute></xsl:if>
                                    <xsl:if test="description">
                                        <description>
                                            <xsl:if test="description/@type"><xsl:attribute name="type"><xsl:value-of select="description/@type" /></xsl:attribute></xsl:if>
                                            <xsl:for-each select="description">
                                                <narrative>
                                                    <xsl:if test="@xml:lang"><xsl:attribute name="xml:lang"><xsl:value-of select="@xml:lang" /></xsl:attribute></xsl:if>
                                                    <xsl:value-of select="text()" />
                                                </narrative>
                                            </xsl:for-each>
                                        </description>
                                    </xsl:if>
                                </budget-item>
                            </xsl:for-each>
                        </country-budget-items>
                    </xsl:if>

                    <xsl:for-each select="policy-marker">
                        <policy-marker>
                            <xsl:if test="@code"><xsl:attribute name="code"><xsl:value-of select="@code" /></xsl:attribute></xsl:if>
                            <xsl:if test="@vocabulary = 'DAC'"><xsl:attribute name="vocabulary">1</xsl:attribute></xsl:if>
                            <xsl:if test="@vocabulary = 'RO'"><xsl:attribute name="vocabulary">99</xsl:attribute></xsl:if>
                            <xsl:if test="@significance"><xsl:attribute name="significance"><xsl:value-of select="@significance" /></xsl:attribute></xsl:if>
                            <narrative>
                                <xsl:if test="@xml:lang"><xsl:attribute name="xml:lang"><xsl:value-of select="@xml:lang" /></xsl:attribute></xsl:if>
                                <xsl:value-of select="text()" />
                            </narrative>
                        </policy-marker>
                    </xsl:for-each>

                    <xsl:if test="collaboration-type">
                        <collaboration-type>
                            <xsl:if test="collaboration-type/@code"><xsl:attribute name="code"><xsl:value-of select="collaboration-type/@code" /></xsl:attribute></xsl:if>
                        </collaboration-type>
                    </xsl:if>

                    <xsl:if test="default-flow-type">
                        <default-flow-type>
                            <xsl:if test="default-flow-type/@code"><xsl:attribute name="code"><xsl:value-of select="default-flow-type/@code" /></xsl:attribute></xsl:if>
                        </default-flow-type>
                    </xsl:if>

                    <xsl:if test="default-finance-type">
                        <default-finance-type>
                            <xsl:if test="default-finance-type/@code"><xsl:attribute name="code"><xsl:value-of select="default-finance-type/@code" /></xsl:attribute></xsl:if>
                        </default-finance-type>
                    </xsl:if>

                    <xsl:if test="default-aid-type">
                        <default-aid-type>
                            <xsl:if test="default-aid-type/@code"><xsl:attribute name="code"><xsl:value-of select="default-aid-type/@code" /></xsl:attribute></xsl:if>
                        </default-aid-type>
                    </xsl:if>

                    <xsl:if test="default-tied-status">
                        <default-tied-status>
                            <xsl:if test="default-tied-status/@code"><xsl:attribute name="code"><xsl:value-of select="default-tied-status/@code" /></xsl:attribute></xsl:if>
                        </default-tied-status>
                    </xsl:if>

                    <xsl:for-each select="budget">
                        <budget>
                            <xsl:if test="@type"><xsl:attribute name="type"><xsl:value-of select="@type" /></xsl:attribute></xsl:if>
                            <period-start>
                                <xsl:if test="period-start/@iso-date"><xsl:attribute name="iso-date"><xsl:value-of select="period-start/@iso-date" /></xsl:attribute></xsl:if>
                            </period-start>
                            <period-end>
                                <xsl:if test="period-end/@iso-date"><xsl:attribute name="iso-date"><xsl:value-of select="period-end/@iso-date" /></xsl:attribute></xsl:if>
                            </period-end>
                            <value>
                                <xsl:if test="value/@currency"><xsl:attribute name="currency"><xsl:value-of select="value/@currency" /></xsl:attribute></xsl:if>
                                <xsl:if test="value/@value-date"><xsl:attribute name="value-date"><xsl:value-of select="value/@value-date" /></xsl:attribute></xsl:if>
                                <xsl:value-of select="value/text()" />
                            </value>
                        </budget>
                    </xsl:for-each>

                    <xsl:for-each select="planned-disbursement">
                        <planned-disbursement>
                            <period-start>
                                <xsl:if test="period-start/@iso-date"><xsl:attribute name="iso-date"><xsl:value-of select="period-start/@iso-date" /></xsl:attribute></xsl:if>
                            </period-start>
                            <period-end>
                                <xsl:if test="period-end/@iso-date"><xsl:attribute name="iso-date"><xsl:value-of select="period-end/@iso-date" /></xsl:attribute></xsl:if>
                            </period-end>
                            <value>
                                <xsl:if test="value/@currency"><xsl:attribute name="currency"><xsl:value-of select="value/@currency" /></xsl:attribute></xsl:if>
                                <xsl:if test="value/@value-date"><xsl:attribute name="value-date"><xsl:value-of select="value/@value-date" /></xsl:attribute></xsl:if>
                                <xsl:value-of select="value/text()" />
                            </value>
                        </planned-disbursement>
                    </xsl:for-each>

                    <xsl:if test="capital-spend">
                        <capital-spend>
                            <xsl:if test="capital-spend/@percentage"><xsl:attribute name="percentage"><xsl:value-of select="capital-spend/@percentage" /></xsl:attribute></xsl:if>
                        </capital-spend>
                    </xsl:if>

                    <xsl:for-each select="transaction">
                        <transaction>
                            <xsl:if test="@ref"><xsl:attribute name="ref"><xsl:value-of select="@ref" /></xsl:attribute></xsl:if>
                            <xsl:if test="transaction-type">
                                <transaction-type>
                                    <xsl:if test="transaction-type/@code = 'IF'"><xsl:attribute name="code">1</xsl:attribute></xsl:if>
                                    <xsl:if test="transaction-type/@code = 'C'"><xsl:attribute name="code">2</xsl:attribute></xsl:if>
                                    <xsl:if test="transaction-type/@code = 'D'"><xsl:attribute name="code">3</xsl:attribute></xsl:if>
                                    <xsl:if test="transaction-type/@code = 'E'"><xsl:attribute name="code">4</xsl:attribute></xsl:if>
                                    <xsl:if test="transaction-type/@code = 'IR'"><xsl:attribute name="code">5</xsl:attribute></xsl:if>
                                    <xsl:if test="transaction-type/@code = 'LR'"><xsl:attribute name="code">6</xsl:attribute></xsl:if>
                                    <xsl:if test="transaction-type/@code = 'R'"><xsl:attribute name="code">7</xsl:attribute></xsl:if>
                                    <xsl:if test="transaction-type/@code = 'QP'"><xsl:attribute name="code">8</xsl:attribute></xsl:if>
                                    <xsl:if test="transaction-type/@code = 'QS'"><xsl:attribute name="code">9</xsl:attribute></xsl:if>
                                    <xsl:if test="transaction-type/@code = 'CG'"><xsl:attribute name="code">10</xsl:attribute></xsl:if>
                                </transaction-type>
                            </xsl:if>
                            <xsl:if test="transaction-date">
                                <transaction-date>
                                    <xsl:if test="transaction-date/@iso-date"><xsl:attribute name="iso-date"><xsl:value-of select="transaction-date/@iso-date" /></xsl:attribute></xsl:if>
                                </transaction-date>
                            </xsl:if>
                            <xsl:if test="value">
                                <value>
                                    <xsl:if test="value/@currency"><xsl:attribute name="currency"><xsl:value-of select="value/@currency" /></xsl:attribute></xsl:if>
                                    <xsl:if test="value/@value-date"><xsl:attribute name="value-date"><xsl:value-of select="value/@value-date" /></xsl:attribute></xsl:if>
                                    <xsl:value-of select="value/text()" />
                                </value>
                            </xsl:if>
                            <xsl:if test="description">
                                <description>
                                    <xsl:for-each select="description">
                                        <narrative>
                                            <xsl:if test="@xml:lang"><xsl:attribute name="xml:lang"><xsl:value-of select="@xml:lang" /></xsl:attribute></xsl:if>
                                            <xsl:value-of select="text()" />
                                        </narrative>
                                    </xsl:for-each>
                                </description>
                            </xsl:if>
                            <xsl:if test="provider-org">
                                <provider-org>
                                    <xsl:if test="provider-org/@provider-activity-id"><xsl:attribute name="provider-activity-id"><xsl:value-of select="provider-org/@provider-activity-id" /></xsl:attribute></xsl:if>
                                    <xsl:if test="provider-org/@ref"><xsl:attribute name="ref"><xsl:value-of select="provider-org/@ref" /></xsl:attribute></xsl:if>
                                    <narrative>
                                        <xsl:if test="provider-org/@xml:lang"><xsl:attribute name="xml:lang"><xsl:value-of select="provider-org/@xml:lang" /></xsl:attribute></xsl:if>
                                        <xsl:value-of select="provider-org/text()" />
                                    </narrative>
                                </provider-org>
                            </xsl:if>
                            <xsl:if test="receiver-org">
                                <receiver-org>
                                    <xsl:if test="receiver-org/@receiver-activity-id"><xsl:attribute name="receiver-activity-id"><xsl:value-of select="receiver-org/@receiver-activity-id" /></xsl:attribute></xsl:if>
                                    <xsl:if test="receiver-org/@ref"><xsl:attribute name="ref"><xsl:value-of select="receiver-org/@ref" /></xsl:attribute></xsl:if>
                                    <narrative>
                                        <xsl:if test="receiver-org/@xml:lang"><xsl:attribute name="xml:lang"><xsl:value-of select="receiver-org/@xml:lang" /></xsl:attribute></xsl:if>
                                        <xsl:value-of select="receiver-org/text()" />
                                    </narrative>
                                </receiver-org>
                            </xsl:if>
                            <xsl:if test="disbursement-channel">
                                <disbursement-channel>
                                    <xsl:if test="disbursement-channel/@code"><xsl:attribute name="code"><xsl:value-of select="disbursement-channel/@code" /></xsl:attribute></xsl:if>
                                </disbursement-channel>
                            </xsl:if>
                            <xsl:if test="flow-type">
                                <flow-type>
                                    <xsl:if test="flow-type/@code"><xsl:attribute name="code"><xsl:value-of select="flow-type/@code" /></xsl:attribute></xsl:if>
                                </flow-type>
                            </xsl:if>
                            <xsl:if test="finance-type">
                                <finance-type>
                                    <xsl:if test="finance-type/@code"><xsl:attribute name="code"><xsl:value-of select="finance-type/@code" /></xsl:attribute></xsl:if>
                                </finance-type>
                            </xsl:if>
                            <xsl:if test="aid-type">
                                <aid-type>
                                    <xsl:if test="aid-type/@code"><xsl:attribute name="code"><xsl:value-of select="aid-type/@code" /></xsl:attribute></xsl:if>
                                </aid-type>
                            </xsl:if>
                            <xsl:if test="tied-status">
                                <tied-status>
                                    <xsl:if test="tied-status/@code"><xsl:attribute name="code"><xsl:value-of select="tied-status/@code" /></xsl:attribute></xsl:if>
                                </tied-status>
                            </xsl:if>
                        </transaction>
                    </xsl:for-each>

                    <xsl:for-each select="document-link">
                        <document-link>
                            <xsl:if test="@url"><xsl:attribute name="url"><xsl:value-of select="@url" /></xsl:attribute></xsl:if>
                            <xsl:if test="@format"><xsl:attribute name="format"><xsl:value-of select="@format" /></xsl:attribute></xsl:if>

                            <xsl:if test="title">
                                <title>
                                    <xsl:for-each select="title">
                                        <narrative>
                                            <xsl:if test="@xml:lang"><xsl:attribute name="xml:lang"><xsl:value-of select="@xml:lang" /></xsl:attribute></xsl:if>
                                            <xsl:value-of select="text()" />
                                        </narrative>
                                    </xsl:for-each>
                                </title>
                            </xsl:if>
                            <xsl:for-each select="category">
                                <category>
                                    <xsl:if test="@code"><xsl:attribute name="code"><xsl:value-of select="@code" /></xsl:attribute></xsl:if>
                                </category>
                            </xsl:for-each>
                            <xsl:for-each select="language">
                                <language>
                                    <xsl:if test="@code"><xsl:attribute name="code"><xsl:value-of select="@code" /></xsl:attribute></xsl:if>
                                </language>
                            </xsl:for-each>
                        </document-link>
                    </xsl:for-each>

                    <xsl:if test="activity-website">
                        <document-link format="text/html">
                            <xsl:attribute name="url"><xsl:value-of select="activity-website/text()" /></xsl:attribute>
                            <title>
                                <narrative xml:lang="en">Activity website</narrative>
                            </title>
                            <category code="A12" />
                        </document-link>
                    </xsl:if>

                    <xsl:for-each select="related-activity">
                        <related-activity>
                            <xsl:if test="@ref"><xsl:attribute name="ref"><xsl:value-of select="@ref" /></xsl:attribute></xsl:if>
                            <xsl:if test="@type"><xsl:attribute name="type"><xsl:value-of select="@type" /></xsl:attribute></xsl:if>
                        </related-activity>
                    </xsl:for-each>

                    <xsl:for-each select="legacy-data">
                        <legacy-data>
                            <xsl:if test="@name"><xsl:attribute name="name"><xsl:value-of select="@name" /></xsl:attribute></xsl:if>
                            <xsl:if test="@value"><xsl:attribute name="value"><xsl:value-of select="@value" /></xsl:attribute></xsl:if>
                            <xsl:if test="@iati-equivalent"><xsl:attribute name="iati-equivalent"><xsl:value-of select="@iati-equivalent" /></xsl:attribute></xsl:if>
                        </legacy-data>
                    </xsl:for-each>

                    <xsl:if test="conditions">
                        <conditions>
                            <xsl:if test="conditions/@attached"><xsl:attribute name="attached"><xsl:value-of select="conditions/@attached" /></xsl:attribute></xsl:if>
                            <xsl:for-each select="conditions/condition">
                            <condition>
                                <xsl:if test="@type"><xsl:attribute name="type"><xsl:value-of select="@type" /></xsl:attribute></xsl:if>
                                <narrative>
                                    <xsl:if test="@xml:lang"><xsl:attribute name="xml:lang"><xsl:value-of select="@xml:lang" /></xsl:attribute></xsl:if>
                                    <xsl:value-of select="text()" />
                                </narrative>
                            </condition>
                            </xsl:for-each>
                        </conditions>
                    </xsl:if>

                    <xsl:for-each select="result">
                        <result>
                            <xsl:if test="@type"><xsl:attribute name="type"><xsl:value-of select="@type" /></xsl:attribute></xsl:if>
                            <xsl:if test="@aggregation-status"><xsl:attribute name="aggregation-status"><xsl:value-of select="@aggregation-status" /></xsl:attribute></xsl:if>

                            <xsl:if test="title">
                                <title>
                                    <xsl:for-each select="title">
                                        <narrative>
                                            <xsl:if test="@xml:lang"><xsl:attribute name="xml:lang"><xsl:value-of select="@xml:lang" /></xsl:attribute></xsl:if>
                                            <xsl:value-of select="text()" />
                                        </narrative>
                                    </xsl:for-each>
                                </title>
                            </xsl:if>
                            <xsl:if test="description">
                                <description>
                                    <xsl:for-each select="description">
                                        <narrative>
                                            <xsl:if test="@xml:lang"><xsl:attribute name="xml:lang"><xsl:value-of select="@xml:lang" /></xsl:attribute></xsl:if>
                                            <xsl:value-of select="text()" />
                                        </narrative>
                                    </xsl:for-each>
                                </description>
                            </xsl:if>

                            <xsl:for-each select="indicator">
                                <indicator>
                                    <xsl:if test="@measure"><xsl:attribute name="measure"><xsl:value-of select="@measure" /></xsl:attribute></xsl:if>
                                    <xsl:if test="@ascending"><xsl:attribute name="ascending"><xsl:value-of select="@ascending" /></xsl:attribute></xsl:if>
                                    <xsl:if test="title">
                                        <title>
                                            <xsl:for-each select="title">
                                                <narrative>
                                                    <xsl:if test="@xml:lang"><xsl:attribute name="xml:lang"><xsl:value-of select="@xml:lang" /></xsl:attribute></xsl:if>
                                                    <xsl:value-of select="text()" />
                                                </narrative>
                                            </xsl:for-each>
                                        </title>
                                    </xsl:if>
                                    <xsl:if test="description">
                                        <description>
                                            <xsl:for-each select="description">
                                                <narrative>
                                                    <xsl:if test="@xml:lang"><xsl:attribute name="xml:lang"><xsl:value-of select="@xml:lang" /></xsl:attribute></xsl:if>
                                                    <xsl:value-of select="text()" />
                                                </narrative>
                                            </xsl:for-each>
                                        </description>
                                    </xsl:if>
                                    <xsl:for-each select="baseline">
                                        <baseline>
                                            <xsl:if test="@year"><xsl:attribute name="year"><xsl:value-of select="@year" /></xsl:attribute></xsl:if>
                                            <xsl:if test="@value"><xsl:attribute name="value"><xsl:value-of select="@value" /></xsl:attribute></xsl:if>
                                            <xsl:if test="comment">
                                                <comment>
                                                    <xsl:for-each select="comment">
                                                        <narrative>
                                                            <xsl:if test="@xml:lang"><xsl:attribute name="xml:lang"><xsl:value-of select="@xml:lang" /></xsl:attribute></xsl:if>
                                                            <xsl:value-of select="text()" />
                                                        </narrative>
                                                    </xsl:for-each>
                                                </comment>
                                            </xsl:if>
                                        </baseline>
                                    </xsl:for-each>
                                    <xsl:for-each select="period">
                                        <period>
                                            <xsl:if test="period-start">
                                                <period-start>
                                                    <xsl:if test="period-start/@iso-date"><xsl:attribute name="iso-date"><xsl:value-of select="period-start/@iso-date" /></xsl:attribute></xsl:if>
                                                </period-start>
                                            </xsl:if>
                                            <xsl:if test="period-end">
                                                <period-end>
                                                    <xsl:if test="period-end/@iso-date"><xsl:attribute name="iso-date"><xsl:value-of select="period-end/@iso-date" /></xsl:attribute></xsl:if>
                                                </period-end>
                                            </xsl:if>
                                            <xsl:for-each select="target">
                                                <target>
                                                    <xsl:if test="@year"><xsl:attribute name="year"><xsl:value-of select="@year" /></xsl:attribute></xsl:if>
                                                    <xsl:if test="@value"><xsl:attribute name="value"><xsl:value-of select="@value" /></xsl:attribute></xsl:if>
                                                    <xsl:if test="comment">
                                                        <comment>
                                                            <xsl:for-each select="comment">
                                                                <narrative>
                                                                    <xsl:if test="@xml:lang"><xsl:attribute name="xml:lang"><xsl:value-of select="@xml:lang" /></xsl:attribute></xsl:if>
                                                                    <xsl:value-of select="text()" />
                                                                </narrative>
                                                            </xsl:for-each>
                                                        </comment>
                                                    </xsl:if>
                                                </target>
                                            </xsl:for-each>
                                            <xsl:for-each select="actual">
                                                <actual>
                                                    <xsl:if test="@year"><xsl:attribute name="year"><xsl:value-of select="@year" /></xsl:attribute></xsl:if>
                                                    <xsl:if test="@value"><xsl:attribute name="value"><xsl:value-of select="@value" /></xsl:attribute></xsl:if>
                                                    <xsl:if test="comment">
                                                        <comment>
                                                            <xsl:for-each select="comment">
                                                                <narrative>
                                                                    <xsl:if test="@xml:lang"><xsl:attribute name="xml:lang"><xsl:value-of select="@xml:lang" /></xsl:attribute></xsl:if>
                                                                    <xsl:value-of select="text()" />
                                                                </narrative>
                                                            </xsl:for-each>
                                                        </comment>
                                                    </xsl:if>
                                                </actual>
                                            </xsl:for-each>
                                        </period>
                                    </xsl:for-each>
                                </indicator>
                            </xsl:for-each>
                        </result>
                    </xsl:for-each>

                    <xsl:for-each select="crs-add">
                        <crs-add>
                            <xsl:for-each select="aidtype-flag">
                                <other-flags>
                                    <xsl:if test="@code"><xsl:attribute name="code"><xsl:value-of select="@code" /></xsl:attribute></xsl:if>
                                    <xsl:if test="@significance"><xsl:attribute name="significance"><xsl:value-of select="@significance" /></xsl:attribute></xsl:if>
                                </other-flags>
                            </xsl:for-each>
                            <xsl:for-each select="loan-terms">
                                <loan-terms>
                                    <xsl:if test="@rate-1"><xsl:attribute name="rate-1"><xsl:value-of select="@rate-1" /></xsl:attribute></xsl:if>
                                    <xsl:if test="@rate-2"><xsl:attribute name="rate-2"><xsl:value-of select="@rate-2" /></xsl:attribute></xsl:if>
                                    <xsl:if test="repayment-type">
                                        <repayment-type>
                                            <xsl:if test="repayment-type/@code"><xsl:attribute name="code"><xsl:value-of select="repayment-type/@code" /></xsl:attribute></xsl:if>
                                        </repayment-type>
                                    </xsl:if>
                                    <xsl:if test="repayment-plan">
                                        <repayment-plan>
                                            <xsl:if test="repayment-plan/@code"><xsl:attribute name="code"><xsl:value-of select="repayment-plan/@code" /></xsl:attribute></xsl:if>
                                        </repayment-plan>
                                    </xsl:if>
                                    <xsl:if test="commitment-date">
                                        <commitment-date>
                                            <xsl:if test="commitment-date/@iso-date"><xsl:attribute name="iso-date"><xsl:value-of select="commitment-date/@iso-date" /></xsl:attribute></xsl:if>
                                        </commitment-date>
                                    </xsl:if>
                                    <xsl:if test="repayment-first-date">
                                        <repayment-first-date>
                                            <xsl:if test="repayment-first-date/@iso-date"><xsl:attribute name="iso-date"><xsl:value-of select="repayment-first-date/@iso-date" /></xsl:attribute></xsl:if>
                                        </repayment-first-date>
                                    </xsl:if>
                                    <xsl:if test="repayment-final-date">
                                        <repayment-final-date>
                                            <xsl:if test="repayment-final-date/@iso-date"><xsl:attribute name="iso-date"><xsl:value-of select="repayment-final-date/@iso-date" /></xsl:attribute></xsl:if>
                                        </repayment-final-date>
                                    </xsl:if>
                                </loan-terms>
                            </xsl:for-each>
                            <xsl:for-each select="loan-status">
                                <loan-status>
                                    <xsl:if test="@year"><xsl:attribute name="year"><xsl:value-of select="@year" /></xsl:attribute></xsl:if>
                                    <xsl:if test="@currency"><xsl:attribute name="currency"><xsl:value-of select="@currency" /></xsl:attribute></xsl:if>
                                    <xsl:if test="@value-date"><xsl:attribute name="value-date"><xsl:value-of select="@value-date" /></xsl:attribute></xsl:if>
                                    <xsl:if test="interest-received">
                                        <interest-received>
                                            <xsl:value-of select="interest-received/text()" />
                                        </interest-received>
                                    </xsl:if>
                                    <xsl:if test="principal-outstanding">
                                        <principal-outstanding>
                                            <xsl:value-of select="principal-outstanding/text()" />
                                        </principal-outstanding>
                                    </xsl:if>
                                    <xsl:if test="principal-arrears">
                                        <principal-arrears>
                                            <xsl:value-of select="principal-arrears/text()" />
                                        </principal-arrears>
                                    </xsl:if>
                                    <xsl:if test="interest-arrears">
                                        <interest-arrears>
                                            <xsl:value-of select="interest-arrears/text()" />
                                        </interest-arrears>
                                    </xsl:if>
                                </loan-status>
                            </xsl:for-each>
                        </crs-add>
                    </xsl:for-each>

                    <xsl:for-each select="fss">
                        <fss>
                            <xsl:if test="@extraction-date"><xsl:attribute name="extraction-date"><xsl:value-of select="@extraction-date" /></xsl:attribute></xsl:if>
                            <xsl:if test="@priority"><xsl:attribute name="priority"><xsl:value-of select="@priority" /></xsl:attribute></xsl:if>
                            <xsl:if test="@phaseout-year"><xsl:attribute name="phaseout-year"><xsl:value-of select="@phaseout-year" /></xsl:attribute></xsl:if>
                            <xsl:for-each select="forecast">
                                <forecast>
                                    <xsl:if test="@year"><xsl:attribute name="year"><xsl:value-of select="@year" /></xsl:attribute></xsl:if>
                                    <xsl:if test="@currency"><xsl:attribute name="currency"><xsl:value-of select="@currency" /></xsl:attribute></xsl:if>
                                    <xsl:if test="@value-date"><xsl:attribute name="value-date"><xsl:value-of select="@value-date" /></xsl:attribute></xsl:if>
                                </forecast>
                            </xsl:for-each>
                        </fss>
                    </xsl:for-each>
                </iati-activity>
            </xsl:for-each>
        </iati-activities>
    </xsl:template>
</xsl:stylesheet>
