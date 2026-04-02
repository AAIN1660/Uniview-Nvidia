import React, { useState, useEffect, ChangeEvent } from "react";
import {
    Box,
    Button,
    Flex,
    Grid,
    Input,
    Stack,
    Text,
    Tabs,
    RadioGroup
} from "@chakra-ui/react";
// import { Radio, RadioGroup } from '@chakra-ui/react'
import { DocumentEdit24Regular, Save24Filled, DismissSquare24Filled } from "@fluentui/react-icons";
import LoadingOverlay from "../../components/LoadingOverlay/LoadingOverlay";
import configurationService from "../../api/configurationService";
import { PrimaryButton } from "@fluentui/react";

interface ConfigItem {
    id: string;
    [key: string]: any;
}

const Configuration: React.FC = ({tabId}) => {
    const [configData, setConfigData] = useState<ConfigItem[]>([]);
    const [editId, setEditId] = useState<string | null>(null);
    const [tempData, setTempData] = useState<ConfigItem | null>(null);
    const [isLoading, setIsLoading] = useState(false);
    const [isLoadingIndex, setIsLoadingIndex] = useState(false);
    const [isUpdating, setIsUpdating] = useState(false);
    const [isUpdatingIndex, setIsUpdatingIndex] = useState(false);
    const [warningMsg, setWarningMsg] = useState("");
    const [isSuperAdminNew, setIsSuperAdminNew] = useState(
        localStorage.getItem("role") === "superAdmin"
    );
    const [index, setIndex] = useState("vector");


    const keysToDisplay = [
        "Total_User_License",
        "Pending_User_License",
        "Use_Credit_Pool",
        "Total_Credit_Pool",
        "Balance_Credit_Pool",
        "Token_Per_Credit",
        "server",
        "user",
    ];

    // Fetch configuration data
    const fetchConfigData = async () => {
        setIsLoading(true);
        try {

            const response = await configurationService.getConfigurationDetails();
            const transformedData = transformResponse(response.data.config_data);
            setConfigData(transformedData);
            setIndex(transformedData[0].search_type)

        } catch (error) {
            console.error("Error fetching configuration data:", error);
        } finally {
            setIsLoading(false);
        }
    };

    // Transform API response
    const transformResponse = (data: any[]) => {
        return data.map((item) => ({
            id: item.id,
            Total_User_License: item.total_license,
            Pending_User_License: item.pending_license,
            Use_Credit_Pool: item.use_credit_pool,
            Total_Credit_Pool: item.credit_pool_assigned,
            Balance_Credit_Pool: item.credit_pool_balance,
            Token_Per_Credit: item.tokens_per_credit,
            search_type: item.search_type
        }));
    };

    useEffect(() => {
        fetchConfigData();
    }, [tabId === "configuration"]);

    // Start editing
    const handleEditClick = (id: string) => {
        setEditId(id);
        const currentItem = configData.find((item) => item.id === id) || null;
        setTempData(currentItem);
    };

    // Handle input change
    const handleChange = (key: string, value: string | boolean) => {
        if (tempData) {
            setTempData({
                ...tempData,
                [key]: value,
            });
        }
    };


    // Save updated data
    const handleSaveIndex = async () => {
        console.log('====================================');
        console.log(tempData);
        console.log('====================================');
        let payload = {
            "search_type": index
        }
        console.log('====================================');
        console.log(payload);
        console.log('====================================');

        try {
            setIsUpdatingIndex(true);
            const response = await configurationService.updateConfig(payload);
            if (response.status === 200) {
                // Update local data
                setIndex(index)
                alert("Updated Successfully")
            }
        } catch (error) {
            console.error("Error saving indexing:", error);
        } finally {
            setIsUpdatingIndex(false);
        }
    };

    // Save updated data
    const handleSave = async () => {
        console.log('====================================');
        console.log(tempData);
        console.log('====================================');
        let payload = {

            "credit_pool_assigned": tempData.Total_Credit_Pool,
            "credit_pool_balance": tempData.Balance_Credit_Pool,
            "total_license": tempData.Total_User_License,
            "pending_license": tempData.Pending_User_License,
            "use_credit_pool": tempData.Use_Credit_Pool,
            "search_type": "hybrid",
            "tokens": tempData.Token_Per_Credit,



        }
        console.log('====================================');
        console.log(payload);
        console.log('====================================');

        if (tempData) {
            try {
                setIsUpdating(true);
                const response = await configurationService.updateConfig(payload);
                if (response.status === 200) {
                    // Update local data
                    setConfigData((prev) =>
                        prev.map((item) => (item.id === tempData.id ? tempData : item))
                    );
                    setEditId(null);
                    setTempData(null);
                    setWarningMsg("");
                    alert("Updated Successfully")
                }
            } catch (error) {
                console.error("Error saving configuration:", error);
            } finally {
                setIsUpdating(false);
            }
        }
    };

    // Cancel editing
    const handleCancel = () => {
        setEditId(null);
        setTempData(null);
        setWarningMsg("");
    };
    // Render component
    if (isLoading) return <LoadingOverlay message="Loading..." />;
    if (isLoadingIndex) return <LoadingOverlay message="Loading..." />;

    return (
        <Box p={2}>
            {/* <Tabs.Root className="workflow-tabs" variant="enclosed" maxW="md" fitted defaultValue={"tab-1"}>
                <Tabs.List>
                    <Tabs.Trigger value="tab-1" minW={'-webkit-fit-content'}>Hybrid (Vec RAG + Graph RAG)</Tabs.Trigger>
                    <Tabs.Trigger value="tab-2" minW={'-webkit-fit-content'}>Vec RAG</Tabs.Trigger>
                    <Tabs.Trigger value="tab-3" minW={'-webkit-fit-content'}>Graph RAG</Tabs.Trigger>
                </Tabs.List>
            </Tabs.Root> */}
            <span className="paddedspan">
                <label className="radio-btnname">
                    <input
                        type="radio"
                        className="mx-1 Radio-Input"
                        name="index"
                        value="vector"
                        onChange={() => setIndex("vector")}
                        checked={index === "vector"}
                    />
                    Vector RAG
                </label>
            </span>
            <span className="paddedspan">
                <label className="radio-btnname">
                    <input
                        type="radio"
                        className="mx-1  Radio-Input"
                        name="index"
                        value="graph"
                        onChange={() => setIndex("graph")}
                        checked={index === "graph"}
                    />
                    Graph RAG
                </label>
            </span>
            <span className="paddedspan">
                <label className="radio-btnname">
                    <input
                        type="radio"
                        className="mx-1 Radio-Input"
                        name="index"
                        value="hybrid"
                        onChange={() => setIndex("hybrid")}
                        checked={index === "hybrid"}
                    />
                    Hybrid (Vec RAG + Graph RAG)
                </label>
            </span>
            <span className="btn-save-index">
                {/* <Button
                className="btn btn-primary color-white"
                style={{ marginLeft: "10px" }}
                onClick={handleSaveIndex}
                // isLoadingIndex={isUpdatingIndex}
            >
                Save
            </Button> */}
                {/* <button className="btn btn-green">
                    Save
            </button> */}
                <Button
                    className="create-btn btn-sm"
                    style={{ marginLeft: "10px",marginTop: "-1px !important"
                    }}
                    variant="primary"
                    onClick={handleSaveIndex}
                >
                    Submit
                </Button>

            </span>
            {isSuperAdminNew && <Grid templateColumns="repeat(3, 1fr)" gap={2}  >
                {configData.map((item) => (
                    <Box key={item.id} p={4} borderWidth={1} borderRadius={8} bg="white" height={370}>
                        <Flex justify="space-between" align="center" mb={4}>
                            <Text fontSize="lg" fontWeight="medium" whiteSpace="nowrap" >
                                {item.id}
                            </Text>
                            {editId === item.id ? (
                                <Flex gap={2}>
                                    <Button
                                        colorScheme="blue"
                                        onClick={handleSave}
                                        isLoading={isUpdating}
                                    >
                                        <Save24Filled />
                                    </Button>
                                    <Button colorScheme="red" onClick={handleCancel}>
                                        <DismissSquare24Filled />
                                    </Button>
                                </Flex>
                            ) : (
                                <Button onClick={() => handleEditClick(item.id)}>
                                    <DocumentEdit24Regular />
                                </Button>
                            )}
                        </Flex>
                        <Stack spacing={4}>
                            {Object.entries(item)
                                .filter(([key]) => keysToDisplay.includes(key))
                                .map(([key, value]) => (
                                    <Flex key={key} align="center" justify="space-between">
                                        <Text>{key}</Text>
                                        {editId === item.id ? (
                                            key === "Use_Credit_Pool" ? (
                                                <select
                                                    value={tempData?.[key] ? "true" : "false"}
                                                    onChange={(e: ChangeEvent<HTMLSelectElement>) =>
                                                        handleChange(key, e.target.value === "true")
                                                    }
                                                    style={{
                                                        padding: "8px",
                                                        borderRadius: "4px",
                                                        border: "1px solid #ccc",
                                                        width: "318px",
                                                    }}
                                                    className="form-control"

                                                >
                                                    <option value="true">True</option>
                                                    <option value="false">False</option>
                                                </select>
                                            ) : (
                                                <Input
                                                    value={tempData?.[key] || ""}
                                                    onChange={(e: ChangeEvent<HTMLInputElement>) =>

                                                        handleChange(key, e.target.value)
                                                    }
                                                    width="318px"
                                                />
                                            )
                                        ) : (
                                            <Text>{key === "Use_Credit_Pool" ? value ? "True" : "False" : value.toString()}</Text>
                                        )}
                                    </Flex>
                                ))}

                        </Stack>
                    </Box>
                ))}
            </Grid>}
        </Box>
    );
};

export default Configuration;