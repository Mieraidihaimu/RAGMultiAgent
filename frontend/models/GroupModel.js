/**
 * Group Model
 * Handles persona group data and API interactions
 */
class GroupModel {
    constructor(apiService) {
        this.api = apiService;
        this.groups = [];
    }

    /**
     * Fetch persona groups
     */
    async fetchGroups(userId, includePersonas = true) {
        try {
            const data = await this.api.get(
                `/groups?user_id=${userId}&include_personas=${includePersonas}`
            );
            this.groups = data.groups || [];
            return { success: true, groups: this.groups };
        } catch (error) {
            console.error('Error fetching groups:', error);
            return { success: false, error: error.message };
        }
    }

    /**
     * Fetch personas for a specific group
     */
    async fetchGroupPersonas(groupId) {
        try {
            const data = await this.api.get(`/groups/${groupId}/personas`);
            return { success: true, personas: data.personas || [] };
        } catch (error) {
            console.error('Error fetching group personas:', error);
            return { success: false, error: error.message };
        }
    }

    /**
     * Get all groups
     */
    getAllGroups() {
        return this.groups;
    }

    /**
     * Get group by ID
     */
    getGroupById(groupId) {
        return this.groups.find(g => g.id === groupId);
    }

    /**
     * Clear groups cache
     */
    clear() {
        this.groups = [];
    }
}
