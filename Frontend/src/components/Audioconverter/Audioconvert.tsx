import React, { useState, } from "react";
import { Mic24Filled,MicOff24Filled } from "@fluentui/react-icons";
import * as sdk from "microsoft-cognitiveservices-speech-sdk";
interface props{
  setQuestion:any,
  onSend:(question:string)=>void,
  setaudio:any,
  audio:Boolean

}

export const Audioconvert = ({setQuestion,onSend,setaudio,audio}:props) => {
  //API KEYS
  const ENDPOINT = import.meta.env.VITE_AZURE_OPENAI_ENDPOINT;
  const AZUREAPIKEY = import.meta.env.VITE_AZURE_SPEECH_KEY;
  const REGION = import.meta.env.VITE_AZURE_OPENAI_API_REGION;
  const PAUSETIME=import.meta.env.VITE_PAUSETIME;

  // USE STATE
  const [recognizedText, setRecognizedText] = useState<string>("");
  const [recognizer, setRecognizer] = useState<any>(null);
  const [speechSynthesizer, setSpeechSynthesizer] = useState<any>(null);

  // START MIC
  const startListening = (e: { preventDefault: () => void; }) => {
    e.preventDefault();
       // Initialize the Speech SDK
       const speechConfig = sdk.SpeechConfig.fromSubscription(AZUREAPIKEY, REGION);
       speechConfig.speechRecognitionLanguage = "en-US";
       const recognizerInstance = new sdk.SpeechRecognizer(
         speechConfig,
         sdk.AudioConfig.fromDefaultMicrophoneInput()
       );

       recognizerInstance.speechEndDetectedTimeout = PAUSETIME;
       const synthesizer = new sdk.SpeechSynthesizer(speechConfig);
       setSpeechSynthesizer(synthesizer)


       recognizerInstance.recognizing = (s, e) => {
         console.log(`RECOGNIZING: ${e.result.text}`);
       };

       recognizerInstance.recognized = (s, e) => {
         if (e.result.reason === sdk.ResultReason.RecognizedSpeech) {

           recognizerInstance.stopContinuousRecognitionAsync();
           console.log(`RECOGNIZED: ${e.result.text}`);
           onSend(e.result.text);
           setRecognizedText(e.result.text);
          
          setQuestion(e.result.text)

           setaudio(false);
         } else if (e.result.reason === sdk.ResultReason.NoMatch) {
           recognizerInstance.stopContinuousRecognitionAsync();

           console.log("No speech could be recognized.");
         }
       };

       recognizerInstance.canceled = (s, e) => {
         console.log(`CANCELED: ${e.reason}`);
       };

       setRecognizer(recognizerInstance);
    // if (recognizer) {
      recognizerInstance.startContinuousRecognitionAsync();
      setaudio(true);
      // }
  };
  // STOP MIC
  const stopListening = () => {
    // e.preventDefault();
    if (recognizer) {
      recognizer.stopContinuousRecognitionAsync();
      setaudio(false);
      // sendQuestion()
    }
  };



  return (
    <div>
      {audio?<MicOff24Filled style={{marginTop:-20,cursor: "pointer"}} primaryFill="#fa3d37" onClick={stopListening}/>:<Mic24Filled primaryFill="rgba(115, 118, 225, 1)" onClick={startListening}  style={{marginTop:-20,cursor: "pointer"}} />
      }

    </div>
  );
};
