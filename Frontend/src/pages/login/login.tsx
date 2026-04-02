import React, { useRef, useState } from "react";
import styles from "./login.module.css";
import { trackPromise } from "react-promise-tracker";
import useCredit from "../../api/userCredit";
import userService from "../../api/userService";
import LoadingOverlay from "../../components/LoadingOverlay/LoadingOverlay";
import BgLogo from "../../assets/images/bg-img-1x.png";
import { useNavigate } from "react-router-dom";

const Login = ({ setIsAdmin, setIsSuperAdmin }) => {
  const { setCreditBalance } = useCredit();
  const navigate = useNavigate();

  const emailRef = useRef<HTMLInputElement>(null);
  const passwordRef = useRef<HTMLInputElement>(null);
  const loaderMessage = "Please wait !!!";
  const [loading, setLoading] = useState(false);

  const handleCustomLogin = () => {
    const email = emailRef.current?.value?.trim() || "";
    const password = passwordRef.current?.value || "";
    if (!email || !password) {
      alert("Please enter email and password");
      return;
    }
    setLoading(true);
    trackPromise(
      userService
        .loginUser({ email, password })
        .then((res: any) => {
          if (!res || res?.status !== 200) {
            setLoading(false);
            alert("Login Failed");
            return;
          }
          const token = res?.data?.jwt_token?.token ?? res?.data?.jwt_token;
          localStorage.setItem("accessToken", typeof token === "string" ? token : "");
          localStorage.setItem("email", res?.data?.email);
          localStorage.setItem("name", res?.data?.name ?? "");
          localStorage.setItem("role", res?.data?.role ?? "");
          setIsAdmin(res?.data?.role === "Admin");
          setIsSuperAdmin(res?.data?.role === "superAdmin");
          localStorage.setItem("logintype", "custom");
          setCreditBalance(res?.data?.balance);
          navigate("/layout/chatwindow");
          setLoading(false);
        })
        .catch((err) => {
          console.error(err);
          setLoading(false);
          alert("Login Failed");
        })
    );
  };

  return (
    <div style={{ display: "flex", height: "100vh", overflow: "hidden" }}>
      <img src={BgLogo} style={{ width: "50%", overflow: "hidden" }} alt="" />
      <div style={{ width: "50%", display: "flex", justifyContent: "center" }}>
        {loading && <LoadingOverlay message={loaderMessage} />}
        <div className="login-container mt-5">
          <div className="login-container">
            <div className="login1 div-wrapper d-flex justify-content-center mt-5">
              <div className={styles.logincard}>
                <h6
                  className="header-group mb-3"
                  style={{
                    fontWeight: "600",
                    fontSize: "1.5rem",
                    position: "relative",
                    right: "-74px",
                    top: "4px",
                  }}
                >
                  Sign In
                </h6>
                <input ref={emailRef} type="email" placeholder="Enter Email" autoComplete="username" />
                <input ref={passwordRef} type="password" placeholder="Enter Password" autoComplete="current-password" />
                <button type="button" onClick={handleCustomLogin}>
                  Sign In
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Login;
