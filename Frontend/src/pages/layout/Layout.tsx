import { Outlet, NavLink, Link, useNavigate } from "react-router-dom";
import github from "../../assets/github.svg";
import styles from "./Layout.module.css";
import AffineLogo from '../../assets/affine-logo-1x.png';
import AffineLogosm from '../../assets/affinelogo_sm.png';
import RetravierLogo from '../../assets/ErylLogo.png';
import React, { useEffect, useState } from "react";
import useCredit from "../../api/userCredit";
import Creditstemplate from "../creditstemplate/credittemplate";
import LoadingOverlay from "../../components/LoadingOverlay/LoadingOverlay";
import AffineLogos from "../../assets/affineLogo.png";
import fusionLogo from "../../assets/fusionLogo.png";
import "./Layout.module.css"
import ProfileIcon from "../../assets/profile-icon.png"
const currentDate = new Date();
const currentYear = currentDate.getFullYear();

const Layout = ({ isAdmin, isSuperAdmin, signOutClickHandler: _signOutClickHandler }) => {
    const { creditBalance } = useCredit()
    const [showCreditComponent, setShowCreditComponent] = useState(false);
    const [isLoaded, setIsLoaded] = useState(true);
    const [showDropdown, setShowDropdown] = useState(false);
    console.log('====================================');
    console.log(showDropdown);
    console.log('====================================');
    const navigate = useNavigate();
    console.log("line 20 isAdmin: ", isAdmin)
    console.log("line 21 isSuperAdmin: ", isSuperAdmin)
    let fullName = localStorage.getItem("name") || ""

    useEffect(() => {
        // Simulate a delay for lazy loading
        const timer = setTimeout(() => {
            setIsLoaded(false);
        }, 2000); // 2-second delay

        // Clean up the timer when the component is unmounted
        return () => clearTimeout(timer);
    }, []);

    const openCreditPage = () => {
        navigate('/layout/creditstemplate');
    };

    const customLogout = () => {
        sessionStorage.clear()
        localStorage.clear()
        navigate("/login")
    }
    const toggleDropdown = () => {
        setShowDropdown((prevState) => !prevState);
    };

    const closeDropdown = () => {
        setShowDropdown(false);
    };

    // useEffect(() => {
    //     const handleOutsideClick = (event) => {
    //         if (!event.target.closest(".profile-container")) {
    //             closeDropdown();
    //         }
    //     };

    //     document.addEventListener("click", handleOutsideClick);
    //     return () => {
    //         document.removeEventListener("click", handleOutsideClick);
    //     };
    // }, []);
    // const handleOutsideClick = (event) => {
    //     if (!event.target.closest(".profile-container")) {
    //         closeDropdown();
    //     }
    // };

    // document.addEventListener("click", handleOutsideClick);
    // return () => {
    //     document.removeEventListener("click", handleOutsideClick);
    // };



    return (
        <>
            {isLoaded && <LoadingOverlay message="Please wait..." />}

            <div className={styles.layout}>
                <header className={styles.header} role={"banner"}>
                    <div className={styles.headerContainer}>
                        
                            {/*<h3 className={styles.headerTitle}>GPT + Enterprise data | Sample</h3>*/}
                            <Link to="/layout/chatwindow" className={styles.headerTitleContainer}>
                            <img src={AffineLogos} className="d-inline-block align-left" alt='Affine' />
                            </Link>
                            {/* <img src={fusionLogo} className="d-inline-block align-left uni-logo ms-4" style={{ width: "38%", height: "70%" }}/> */}
                            {/* <span style={{background: 'linear-gradient(to right, #0768ff, #77ff77)',WebkitBackgroundClip: 'text',WebkitTextFillColor: 'transparent', marginLeft: '15px',fontSize:"22px"}}>FusionAI</span> */}
                        
                        <nav className={styles.adminHeader}>
                            <ul className={styles.headerNavList}>

                                <div className="ms-5">
                                    <div className={` ms-5 ${styles.toggleButtonGroupNew}`}>

                                        <NavLink
                                            to="chatwindow"
                                            className={({ isActive }) =>
                                                `${styles.toggleButtonNew} ${isActive ? styles.toggleButtonActiveNew : ""}`
                                            }
                                        >
                                            <i className="fas fa-comment-dots"></i> Ask
                                        </NavLink>
                                        <NavLink
                                            to="uploads"
                                            className={({ isActive }) =>
                                                `${styles.toggleButtonNew} ${isActive ? styles.toggleButtonActiveNew : ""}`
                                            }
                                        >
                                            <i className="fas fa-file-upload"></i> Uploads
                                        </NavLink>

                                        {/* Divider */}
                                        {(isAdmin || isSuperAdmin) && <NavLink
                                            to="admin"
                                            className={({ isActive }) =>
                                                `${styles.toggleButtonNew} ${isActive ? styles.toggleButtonActiveNew : ""}`
                                            }
                                        >
                                            <i className="fas fa-user-friends"></i> Admin
                                        </NavLink>}
                                    </div>
                                </div>

                            </ul>
                        </nav>

                    </div>

                    <div
                        className="creditsbutton pointer "

                        onClick={openCreditPage}
                        style={{background: "linear-gradient(to right, rgb(204, 153, 0), white)", color: "#000"}}
                    >
                        <span
                            className="credit-text pointer"
                            style={{
                                fontSize: "13px", // Adjust font size
                                fontWeight: "600", // Slightly bolder text
                                color: "#000", // Gold/yellow text
                                display: "flex",
                                alignItems: "center",
                            }}
                        >
                            <i className="fas fa-bolt" style={{ marginRight: "5px" }}></i>
                            {creditBalance} credits left
                        </span>
                    </div>



                    <div
                        style={{
                            color: "#fff",
                            fontSize: "15px",
                            margin: "10px",
                            whiteSpace: "nowrap",
                            position: "relative",
                            left: "-20px"
                        }}
                    >
                        {fullName}
                    </div>
                    <div
                        className="profile-picture-container"
                        style={{ position: "relative" }}
                    >
                        <div
                            className="profile-picture pointer"
                            style={{
                                marginLeft: "8px",
                                height: "30px",
                                width: "30px",
                                borderRadius: "50%",
                                overflow: "hidden",
                                cursor: "pointer",
                                marginRight: "16px",
                                position: "relative",
                                right: "17px"
                            }}
                            title="Profile"
                            onClick={toggleDropdown}

                        >
                            <img
                                src={ProfileIcon}
                                alt="Profile"
                                style={{
                                    width: "100%",
                                    height: "100%",
                                    objectFit: "cover",
                                }}
                            />
                        </div>
                        {showDropdown && (

                            <div
                                className="dropdown-menus"
                                style={{
                                    position: "absolute",
                                    top: "47px",
                                    right: "0",
                                    backgroundColor: "#fff",
                                    border: "1px solid #ccc",
                                    borderRadius: "5px",
                                    zIndex: 1004,
                                    padding: "10px",
                                    boxShadow: "0px 4px 6px rgba(0, 0, 0, 0.1)",
                                    display: "flex",
                                    alignItems: "center",
                                    gap: "8px",
                                }}
                            >
                                <i
                                    className="fas fa-power-off"
                                    style={{
                                        color: "grey", // Red color for the icon
                                        fontSize: "16px",
                                    }}
                                ></i>
                                <button
                                    onClick={customLogout}
                                    style={{
                                        background: "none",
                                        border: "none",
                                        color: "#000",
                                        cursor: "pointer",
                                        fontSize: "14px",
                                    }}
                                >
                                    Logout
                                </button>
                            </div>

                        )}
                    </div>


                </header>

                <Outlet />
                {/* <footer className={styles.footer}>
                    <div className={styles.left_container}>
                        <span className={styles.copy_right}>copyright &copy; {currentYear}</span>
                    </div>
                    <div className={styles.powered}>
                        <label className={styles.footertext} >Powered by </label>

                        <a href="https://affine.ai" target="_blank" ><img className={styles.footerlogopos} src={AffineLogo} alt="Affine Logo" /></a>
                    </div>
                </footer> */}
                {showCreditComponent && <Creditstemplate />}
            </div>
        </>
    );
};

export default Layout;