import { GuardianAPI } from '../types';

declare global {
    interface Window {
        guardian: GuardianAPI;
    }
}
