import Category from "../category/CategoryList";
import { Tabs } from "@chakra-ui/react";
import { PeopleCommunity20Filled, Tag20Filled, Settings20Filled, Database20Filled } from "@fluentui/react-icons";
import UsersList from "../users/UsersList";
import "./Admin.scss";
import Configuration from "../configuration/Configuration";
import ConnectionSettings from "../connectionSetings/ConnectionSettings";
import { trackPromise } from "react-promise-tracker";
import categoryService from "../../api/categoryService";
import { useState } from "react";


const Admin = () => {
      const [categoryLoading, setCategoryLoading] = useState<boolean>(true);
          const [allCategories, setAllCategories] = useState([]);
          const [activeTab, setActiveTab] = useState("users");
        
    const handleTabChange = (tabValue) => {
        // alert(tabValue)
        console.log(tabValue)
        if(tabValue.value=== 'users'){
            getCategoryList()
        }
        setActiveTab(tabValue.value)
    }
    const getCategoryList = () => {
        setCategoryLoading(true);
        trackPromise(
          categoryService
            .getCategory({ type: "active" })
            .then((res) => {
              const activeCategories = res?.data?.CategoryList.filter(
                (category) => category.status === 1
              );
              const comboboxOptions = activeCategories.map((category) => ({
                value: category.id,
                label: category.category_name,
              }));
              setAllCategories(comboboxOptions);
              setCategoryLoading(false);
            })
            .catch(() => setCategoryLoading(false))
        );
      };
    return (
        <div className="adminPage" >
            <header role={"banner"}>
                <Tabs.Root defaultValue="users" onValueChange={handleTabChange}>
                    <Tabs.List>
                        <Tabs.Trigger value="users">
                            <PeopleCommunity20Filled />
                            Users
                        </Tabs.Trigger>
                        <Tabs.Trigger value="categories">
                            <Tag20Filled />
                            Categories
                        </Tabs.Trigger>
                        <Tabs.Trigger value="configuration">
                            <Settings20Filled />
                            Configuration
                        </Tabs.Trigger>
                        <Tabs.Trigger value="database-connection">
                            <Database20Filled />
                            DB Connections
                        </Tabs.Trigger>
                    </Tabs.List>
                    <Tabs.Content value="users"><UsersList tabId={activeTab} /></Tabs.Content>
                    <Tabs.Content value="categories"><Category tabId={activeTab} /></Tabs.Content>
                    <Tabs.Content value="configuration">
                        <Configuration tabId={activeTab} />
                    </Tabs.Content>
                    <Tabs.Content value="database-connection">
                        <ConnectionSettings tabId={activeTab} />
                    </Tabs.Content>
                </Tabs.Root>
            </header>
        </div>
    );
};

export default Admin;
