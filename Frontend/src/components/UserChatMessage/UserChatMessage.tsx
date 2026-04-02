import styles from "./UserChatMessage.module.css";

interface Props {
    message: string;
}

export const UserChatMessage = ({ message }: Props) => {
    return (
        <div className={styles.container} style={{maxWidth:"100%",position:"sticky",top:"0",zIndex:"1003",justifyContent: "center", pointerEvents:'none'}}>
            <div className={styles.message} style={{width: "83%",
    marginBottom: "75px"}}>{message}</div>
        </div>
    );
};
