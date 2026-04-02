import React, { useEffect, useState } from 'react';
import { Pivot, PivotItem } from "@fluentui/react";
import DOMPurify from "dompurify";

import "./AnalysisPanel.css";

import { SupportingContent } from "../SupportingContent";
import { AskResponse } from "../../api";
import { AnalysisPanelTabs } from "./AnalysisPanelTabs";

interface Props {
    className: string;
    activeTab: AnalysisPanelTabs;
    onActiveTabChanged: (tab: AnalysisPanelTabs) => void;
    activeCitation: string | undefined;
    citationHeight: string;
    answer: AskResponse;
}

const pivotItemDisabledStyle = { disabled: true, style: { color: "grey" } };



export const AnalysisPanel = ({ answer, activeTab, activeCitation, citationHeight, className, onActiveTabChanged, vector_context,graph_context }: Props) => {
    const isDisabledThoughtProcessTab: boolean = !answer.thoughts;
    const isDisabledSupportingContentTab: boolean = !(vector_context?.chunks?.length ||graph_context?.chunks?.length);
    // const isDisabledCitationTab: boolean = !activeCitation;

    const sanitizedThoughts = DOMPurify.sanitize(answer.thoughts!);

    const [iframeLoaded, setIframeLoaded] = useState(false);
    const [isDisabledCitationTab, setIsDisabledCitationTab] = useState(true); // Assuming you have a state to control if the citation tab is disabled

    useEffect(() => {
        setIframeLoaded(false);
    }, [activeCitation])

    const handleIframeLoad = () => {
        setIframeLoaded(true);
        // Optionally, you can enable the citation tab here
        setIsDisabledCitationTab(false);
    };

    return (
        <Pivot
            className={className}
            selectedKey={activeTab}
            onLinkClick={pivotItem => pivotItem && onActiveTabChanged(pivotItem.props.itemKey! as AnalysisPanelTabs)}
        >
            <PivotItem
                itemKey={AnalysisPanelTabs.ThoughtProcessTab}
                headerText="Thought process"
                headerButtonProps={isDisabledThoughtProcessTab ? pivotItemDisabledStyle : undefined}
            >
                <div className="thoughtProcess" dangerouslySetInnerHTML={{ __html: sanitizedThoughts }}></div>
            </PivotItem>
            <PivotItem
                itemKey={AnalysisPanelTabs.SupportingContentTab}
                headerText="Supporting content"
                headerButtonProps={isDisabledSupportingContentTab ? pivotItemDisabledStyle : undefined}
            >
                <SupportingContent supportingContent={[...(vector_context?.chunks || []), ...(graph_context?.chunks || [])]
 } />
            </PivotItem>
            <PivotItem
                itemKey={AnalysisPanelTabs.CitationTab}
                headerText="Citation"
                headerButtonProps={isDisabledCitationTab ? pivotItemDisabledStyle : undefined}
            >
                {!iframeLoaded && (
                    // Loader icon, you can replace this with your loader component
                    <div className="loader"></div>
                )}
                <iframe
                    title="Citation"
                    src={activeCitation}
                    width="100%"
                    height={citationHeight}
                    onLoad={handleIframeLoad}
                    style={{ display: iframeLoaded ? 'block' : 'none' }}
                />
            </PivotItem>
        </Pivot>
    );
};
