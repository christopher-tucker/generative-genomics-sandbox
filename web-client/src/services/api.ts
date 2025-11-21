import axios from 'axios';
export const generate = (descriptor:any) => axios.post('/generate',{descriptor});
