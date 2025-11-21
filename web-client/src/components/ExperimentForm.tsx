import React, {useState} from 'react';
import axios from 'axios';

export default function ExperimentForm(){
  const [cellType, setCellType] = useState('HEK293');
  const [treatment, setTreatment] = useState('drugX');
  const [dose, setDose] = useState(10);
  const [timepoint, setTimepoint] = useState(24);
  const [result, setResult] = useState<any>(null);
  const run = async () => {
    const payload = {descriptor:{cell_type:cellType,treatment:treatment,dose:Number(dose),timepoint:Number(timepoint)}};
    const res = await axios.post('/generate', payload);
    setResult(res.data);
  };
  return (
    <div>
      <div>
        <label>Cell Type: <input value={cellType} onChange={e=>setCellType(e.target.value)} /></label>
      </div>
      <div>
        <label>Treatment: <input value={treatment} onChange={e=>setTreatment(e.target.value)} /></label>
      </div>
      <div>
        <label>Dose: <input type="number" value={dose} onChange={e=>setDose(Number(e.target.value))} /></label>
      </div>
      <div>
        <label>Timepoint: <input type="number" value={timepoint} onChange={e=>setTimepoint(Number(e.target.value))} /></label>
      </div>
      <button onClick={run}>Generate</button>
      {result && <pre style={{maxHeight:300,overflow:'auto'}}>{JSON.stringify(result,null,2)}</pre>}
    </div>
  );
}
